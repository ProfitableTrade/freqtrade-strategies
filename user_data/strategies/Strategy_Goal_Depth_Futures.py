# --- Do not remove these libs ---
import datetime
import logging
from typing import Optional, Tuple, Union
from freqtrade.strategy import IStrategy, informative
from pandas import DataFrame
from freqtrade.persistence import Trade
from freqtrade.strategy import stoploss_from_open
# --------------------------------

class Strategy_Goal_Depth_Futures(IStrategy):
    """
    Strategy_Goal_Depth_Futures
    author@: Yurii Udaltsov and Illia
    github@: https://github.com/freqtrade/freqtrade-strategies

    How to use it?
    > python3 ./freqtrade/main.py -s Strategy_Goal_Depth
    """

    INTERFACE_VERSION: int = 3
    BE_ACTIVATED: str = "be_activated"
    STAGE_1_SOLD: str = "stage_1_sold"
    STAGE_2_SOLD: str = "stage_2_sold"
    
    position_adjustment_enable = True

    # Оптимальний стоп-лосс або %max, розроблений для стратегії
    stoploss = -0.02
    
    use_custom_stoploss = True
    
    can_short = True

    # Оптимальний таймфрейм для стратегії
    timeframe = '5m'

    # Налаштування трейлінг стоп-лосу
    # trailing_stop = True  # Включення трейлінг стоп-лосу
    # trailing_stop_positive = 0.033  # Трейлінг стоп активується, коли прибуток досягає 3,3%
    # trailing_stop_positive_offset = 0.035  # Трейлінг стоп починає діяти, коли прибуток перевищує 3,5%
    # trailing_only_offset_is_reached = True  # Трейлінг стоп активується тільки після досягнення offset

    # запускати "populate_indicators" тільки для нової свічки
    process_only_new_candles = True

    # Експериментальні параметри (конфігурація має перевагу над ними, якщо встановлено)
    use_exit_signal = True
    exit_profit_only = False

    # Optional order type mapping
    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': True
    }
    
    # Settings for target reaching logic
    target_percent = 0.10
    
    target_stage_1 = 0.03
    target_stage_2 = 0.06
    
    stage_1_sell_amount = 0.3
    stage_2_sell_amount = 0.3
    
    # Settings for check market depth on enter 
    
    bids_to_ask_delta_long = 1.3
    bids_to_ask_delta_short = 0.7
    
    depth_long = 7
    depth_short = 7
    
    volume_threshold_long = 500
    volume_threshold_short = 500
    
    def bot_start(self, **kwargs) -> None:
        self.logger = logging.getLogger(__name__)
        
    @informative(timeframe, candle_type="funding_rate")
    def populate_indicators_funding_rate(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        self.logger.info(dataframe.head(10).to_string())
        dataframe['funding_rate'] = dataframe['open']
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        order_book = self.dp.orderbook(metadata['pair'], max(self.depth_long, self.depth_short) + 1)

        # Відкриття лонгової позиції
        dataframe.loc[
            (self.check_depth_of_market(order_book, self.bids_to_ask_delta_long, self.depth_long)) &  
            (self.analyze_large_orders(order_book, self.volume_threshold_long)) &  
            (dataframe['volume'] > dataframe['volume'].shift(1)) &  
            (dataframe['close'] < dataframe['close'].shift(1)) &  
            (dataframe['funding_rate'] < 0),  
            'enter_long'
            ] = 1
            

        # Відкриття шортової позиції
        dataframe.loc[
            (self.check_depth_of_market(order_book, self.bids_to_ask_delta_short, self.depth_short, is_short=True)) &  
            (self.analyze_large_orders(order_book, self.volume_threshold_short)) &  
            (dataframe['volume'] > dataframe['volume'].shift(1)) &  
            (dataframe['close'] > dataframe['close'].shift(1)) &  
            (dataframe['funding_rate'] > 0),  
            'enter_short'
            ] = 1

        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Generates sell signal based on EMA indicators
        A sell signal is generated when EMA 15 crosses below EMA 30
        """

        return dataframe

    def check_depth_of_market(self, order_book, bids_to_ask_delta=1.3, depth=7, is_short=False) -> bool:
        if len(order_book['bids']) < depth or len(order_book['asks']) < depth:
            return False
        
        total_bids = sum([bid[1] for bid in order_book['bids'][:depth]])
        total_asks = sum([ask[1] for ask in order_book['asks'][:depth]])
        
        if is_short:
            return (total_bids / total_asks) < bids_to_ask_delta  
        else:
            return (total_bids / total_asks) > bids_to_ask_delta  

    def analyze_large_orders(self, order_book, volume_threshold ) -> bool:
        large_orders = [order for order in order_book['bids'] if order[1] >= volume_threshold] + \
                       [order for order in order_book['asks'] if order[1] >= volume_threshold]
        
        return len(large_orders) > 0
    
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: Optional[str], side: str,
                 **kwargs) -> float:
        
        return 3.0
    
    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float, after_fill: bool,
                        **kwargs) -> Optional[float]:
        try:
            be_activated = trade.get_custom_data(self.BE_ACTIVATED, default=False)
            
            current_price_rate = 0
            if trade.is_short:
                current_price_rate = trade.open_rate / current_rate - 1
            else:
                current_price_rate = current_rate / trade.open_rate - 1

            if be_activated or current_price_rate >= self.target_percent * self.target_stage_1:
                if not be_activated: 
                    trade.set_custom_data(self.BE_ACTIVATED, True)
                    
                return stoploss_from_open(0.002, current_profit, is_short=trade.is_short, leverage=trade.leverage)

            return None
        except Exception as e:
            self.logger.info(f"Error occured during custom stoploss definition: {str(e)}")
            return None
    
    def adjust_trade_position(self, trade: Trade, current_time: datetime,
                              current_rate: float, current_profit: float,
                              min_stake: Optional[float], max_stake: float,
                              current_entry_rate: float, current_exit_rate: float,
                              current_entry_profit: float, current_exit_profit: float,
                              **kwargs
                              ) -> Union[Optional[float], Tuple[Optional[float], Optional[str]]]:
        try:
            stage_1_sold = trade.get_custom_data(self.STAGE_1_SOLD, default=False)
            stage_2_sold = trade.get_custom_data(self.STAGE_2_SOLD, default=False)
            
            current_price_rate = 0
            if trade.is_short:
                current_price_rate = trade.open_rate / current_rate - 1
            else:
                current_price_rate = current_rate / trade.open_rate - 1
            
            self.logger.info(f"Check for goal to be closed, price rate {current_price_rate}.")
            
            if not stage_1_sold and current_price_rate >= self.target_stage_1:
                self.logger.info(f"Price rise up bigger than {self.target_percent * self.target_stage_1}, closing first target {self.stage_1_sell_amount}.")
                trade.set_custom_data(self.STAGE_1_SOLD, True)
                return - ( trade.stake_amount * self.stage_1_sell_amount )
            elif not stage_2_sold and current_price_rate >= self.target_stage_2:
                self.logger.info(f"Price rise up bigger than {self.target_percent * self.target_stage_2}, closing second target {self.stage_2_sell_amount}.")
                trade.set_custom_data(self.STAGE_2_SOLD, True)
                return - ( trade.stake_amount * self.stage_2_sell_amount )
            elif current_price_rate >= self.target_percent:
                self.logger.info(f"Price rise up bigger than {self.target_percent}, closing order.")
                return - trade.stake_amount
            else:
                return None
        except Exception as e:
            self.logger.info(f"Error occured during trade position adjustment: {str(e)}")
            return None