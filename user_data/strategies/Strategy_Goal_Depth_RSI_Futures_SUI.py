# --- Do not remove these libs ---
import datetime
import logging
from typing import Optional, Tuple, Union
from freqtrade.strategy import IStrategy, informative
from pandas import DataFrame
from freqtrade.persistence import Trade
from freqtrade.strategy import stoploss_from_open
import talib.abstract as ta
# --------------------------------

class SettingsObject:
    bids_ask_delta: float
    depth: int
    volume_threshold: int
    
    def __init__(self, bids_ask_delta: float, depth: int, volume_threshold: int):
        self.bids_ask_delta = bids_ask_delta
        self.depth = depth
        self.volume_threshold = volume_threshold


class Strategy_Goal_Depth_RSI_Futures_SUI(IStrategy):
    """
    Strategy_Goal_Depth_Futures_SUI 
    author@: Yurii Udaltsov and Illia
    github@: https://github.com/freqtrade/freqtrade-strategies

    How to use it?
    > python3 ./freqtrade/main.py -s Strategy_Goal_Depth
    """

    INTERFACE_VERSION: int = 3
    BE_ACTIVATED: str = "be_activated"
    STAGE_1_SOLD: str = "stage_1_sold"
    STAGE_2_SOLD: str = "stage_2_sold"
    
    # Налаштування для глибини ринку та аналізу обсягів
    STRATEGY_SETTINGS = {
        "5m": SettingsObject(1.3, 15, 20000)
    }
    
    position_adjustment_enable = True

    # Оптимальний стоп-лосс або %max, розроблений для стратегії
    stoploss = -0.03
    
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
    target_percent = 0.03
    
    target_stage_1 = 0.01
    target_stage_2 = 0.02
    
    stage_1_sell_amount = 0.4
    stage_2_sell_amount = 0.6
    
    rsi_period = 14
    rsi_buy_threshold = 35  # Порогове значення для покупки по RSI
    rsi_sell_threshold = 70  # Порогове значення для продажу по RSI
    
    
    def bot_start(self, **kwargs) -> None:
        self.logger = logging.getLogger(__name__)
        self.settings = self.STRATEGY_SETTINGS[self.timeframe]
        
    # @informative(timeframe, candle_type="funding_rate")
    # def populate_indicators_funding_rate(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
    #     self.logger.info(dataframe.head(10).to_string())
    #     dataframe['funding_rate'] = dataframe['open']
    #     return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=self.rsi_period)  # Розрахунок RSI за 14 періодів
        return dataframe
    
    @property
    def plot_config(self):
        plot_config = {}
        plot_config['main_plot'] = {}
        plot_config['subplots'] = {
            # Additional subplot RSI
            "RSI": {
                'rsi': {'color': 'red'}
            }
        }

        return plot_config

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        order_book = self.dp.orderbook(metadata['pair'], self.settings.depth + 1)
    
        # Умови входу за книгою ордерів
        depth_value = self.check_depth_of_market(order_book, self.settings.depth, self.settings.bids_ask_delta)
        large_orders_value = self.analyze_large_orders(order_book, self.settings.volume_threshold)
        volume_value = dataframe['volume'] > dataframe['volume'].shift(1)
        close_value = dataframe['close'] < dataframe['close'].shift(1)
        rsi_condition = dataframe['rsi'] < self.rsi_buy_threshold  # Вхід у лонг при RSI < 35
        
        self.logger.info(f"Depth check: {depth_value}, large orders check: {large_orders_value}, volume check: {volume_value.tail(2)}, close check: {close_value.tail(2)}, rsi check: {dataframe[['date', 'rsi']].tail(2)}")

        # Лонг позиція
        dataframe.loc[
            (depth_value) & (large_orders_value) & (volume_value) & (close_value) & (rsi_condition),
            'enter_long'
        ] = 1

        # Умови на шорт
        rsi_condition_short = dataframe['rsi'] > self.rsi_sell_threshold  # Вхід у шорт при RSI > 70
        close_value_short = dataframe['close'] > dataframe['close'].shift(1)

        dataframe.loc[
            (depth_value) & (large_orders_value) & (volume_value) & (close_value_short) & (rsi_condition_short),
            'enter_short'
        ] = 1

        return dataframe

    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Умови виходу з позиції на основі RSI.
        """
        # Вихід із лонгу при RSI > 70
        dataframe.loc[
            (dataframe['rsi'] > self.rsi_sell_threshold),
            'exit_long'
        ] = 1

        # Вихід із шорту при RSI < 35
        dataframe.loc[
            (dataframe['rsi'] < self.rsi_buy_threshold),
            'exit_short'
        ] = 1

        return dataframe


    def check_depth_of_market(self, order_book, bids_to_ask_delta=1.3, depth=7, is_short=False) -> bool:
        if len(order_book['bids']) < depth or len(order_book['asks']) < depth:
            return False
        
        self.logger.info(f"Orderbook: {order_book.items()}, depth: {depth}")
        
        total_bids = sum([bid[1] for bid in order_book['bids'][:depth]])
        total_asks = sum([ask[1] for ask in order_book['asks'][:depth]])
        
        if is_short:
            return ( total_asks / total_bids ) > bids_to_ask_delta  
        else:
            return ( total_bids / total_asks ) > bids_to_ask_delta  

    def analyze_large_orders(self, order_book, volume_threshold ) -> bool:
        large_orders = [order for order in order_book['bids'] if order[1] >= volume_threshold] + \
                       [order for order in order_book['asks'] if order[1] >= volume_threshold]
        
        return len(large_orders) > 0
    
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: Optional[str], side: str,
                 **kwargs) -> float:
        
        return 4.0
    
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

            if be_activated or current_price_rate >= self.target_stage_1:
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
                self.logger.info(f"Price rise up bigger than {self.target_stage_1}, closing first target {self.stage_1_sell_amount}.")
                trade.set_custom_data(self.STAGE_1_SOLD, True)
                return - ( trade.stake_amount * self.stage_1_sell_amount )
            elif not stage_2_sold and current_price_rate >= self.target_stage_2:
                self.logger.info(f"Price rise up bigger than {self.target_stage_2}, closing second target {self.stage_2_sell_amount}.")
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