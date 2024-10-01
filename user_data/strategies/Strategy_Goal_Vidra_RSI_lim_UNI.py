# --- Do not remove these libs ---
import datetime
import logging
from typing import Optional, Tuple, Union
from freqtrade.strategy import IStrategy, informative
from pandas import DataFrame
from freqtrade.persistence import Trade
import talib.abstract as ta


class SettingsObject:
    bids_ask_delta: float
    depth: int
    volume_threshold: int
    
    def __init__(self, bids_ask_delta: float, depth: int, volume_threshold: int):
        self.bids_ask_delta = bids_ask_delta
        self.depth = depth
        self.volume_threshold = volume_threshold
        


class Strategy_Goal_Vidra_RSI_lim_UNI(IStrategy):
    """
    Strategy_Goal_Vidra_RSI_lim
    author@: Yurii Udaltsov and Illia
    github@: https://github.com/freqtrade/freqtrade-strategies

    How to use it?
    > python3 ./freqtrade/main.py -s Strategy_Goal_Vidra_SOL
    """

    INTERFACE_VERSION: int = 3
    BE_ACTIVATED: str = "be_activated"
    STAGE_SOLD: str = "stage_{stage}_sold"
    STAGE_BOUGHT: str = "stage_{stage}_bought"
    
    STRATEGY_SHEET_NAME = "DepthSpot"
    
    STRATEGY_SETTINGS = {
        "5m": SettingsObject(1.2, 5, 700)
    }
    
    position_adjustment_enable = True
    
    timeframe="5m"

    # Оптимальний стоп-лосс або %max, розроблений для стратегії
    stoploss = -0.1
    

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
        'stoploss_on_exchange': False
    }
    
    # Settings for target reaching logic
    target_percent = 0.1
    
    target_stage_1 = 0.03
    target_stage_2 = 0.06
    
    stage_1_sell_amount = 0.33
    stage_2_sell_amount = 0.5
    
    
    # Step buying (DCA) settings
    dca_levels = [-0.02, -0.04, -0.06, -0.08]  # Levels for additional buy-ins
    dca_buy_amounts = [0.1, 0.1, 0.15, 0.15]  # Buy amounts for each level
    
    rsi_buy_threshold = 35  # Порогове значення для покупки по RSI
    rsi_sell_threshold = 70  # Порогове значення для продажу по RSI


    def bot_start(self, **kwargs) -> None:
        self.logger = logging.getLogger(__name__)
        
        self.settings = self.STRATEGY_SETTINGS[self.timeframe]
        
    @informative('1h')
    def populate_indicators_1h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Generates buy signal based on EMA indicators
        A buy signal is generated when EMA 15 crosses above EMA 30
        """
        
        order_book = self.dp.orderbook(metadata['pair'], self.settings.depth + 1)

        depth_value = self.check_depth_of_market(order_book, self.settings.depth, self.settings.bids_ask_delta)
        large_orders_value = self.analyze_large_orders(order_book, self.settings.volume_threshold)
        volume_value = dataframe['volume'] > dataframe['volume'].shift(1)
        close_value = dataframe['close'] < dataframe['close'].shift(1)
        rsi_buy_condition = dataframe['rsi_1h'] < self.rsi_buy_threshold
        
        self.logger.info(f"Depth check: {depth_value}, large orders check: {large_orders_value}, volume check: {volume_value.tail(2)}, close check: {close_value.tail(2)}, rsi check: {dataframe[['date', 'rsi_1h']].tail(2)}")

        dataframe.loc[
            (depth_value) & (large_orders_value) & (volume_value) & (close_value) & (rsi_buy_condition),
            'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe['rsi_1h'] > self.rsi_sell_threshold),
            'exit_long'
        ] = 1

        return dataframe
    
    def check_depth_of_market(self, order_book, depth, delta, exit=False) -> bool:
        if len(order_book['bids']) < depth or len(order_book['asks']) < depth:
            return False
        
        total_bids = sum([bid[1] for bid in order_book['bids'][:depth]])
        total_asks = sum([ask[1] for ask in order_book['asks'][:depth]])
        
        self.logger.info(f"Analyzing depth of market... Results: total bids / total asks is {total_bids / total_asks}, configured delta is {delta}")
        
        if exit:
            return ( total_asks / total_bids ) > delta  
        else:
            return ( total_bids / total_asks ) > delta  

    def analyze_large_orders(self, order_book, threshold) -> bool:
        large_orders = [order for order in order_book['bids'] if order[1] >= threshold] + \
                       [order for order in order_book['asks'] if order[1] >= threshold]

        self.logger.info(f"Analyzing large orders for threshold {threshold}, found {len(large_orders)}")
        
        return len(large_orders) > 0
    
    
    def adjust_trade_position(self, trade: Trade, current_time: datetime,
                              current_rate: float, current_profit: float,
                              min_stake: Optional[float], max_stake: float,
                              current_entry_rate: float, current_exit_rate: float,
                              current_entry_profit: float, current_exit_profit: float,
                              **kwargs
                              ) -> Union[Optional[float], Tuple[Optional[float], Optional[str]]]:
        try:
            
            time_passed = datetime.datetime.now() - trade.open_date
            if time_passed.days >= 2 and trade.get_custom_data(self.STAGE_SOLD.format(stage=1)):
                # Exit from trade if more than 2 days passed from start and 1 goal is reached
                return - trade.stake_amount
            
            current_price_rate = current_rate / trade.open_rate - 1
            self.logger.info(f"Check for goal to be closed, price rate {current_price_rate}")
            
            # Check if DCA levels are hit
            for level, amount in zip(self.dca_levels, self.dca_buy_amounts):
                if not trade.get_custom_data(self.STAGE_BOUGHT.format(stage=self.dca_levels.index(level)), default=False) and current_price_rate <= level:
                    self.logger.info(f"DCA level {level} reached, buying {amount * 100}% more")
                    trade.set_custom_data(self.STAGE_BOUGHT.format(stage=self.dca_levels.index(level)), True)
                    return amount * trade.stake_amount

            
            if not trade.get_custom_data(self.STAGE_SOLD.format(stage=1), default=False) and current_price_rate >= self.target_stage_1:
                self.logger.info(f"Price rise up bigger than {self.target_stage_1}, closing first target {self.stage_1_sell_amount}")
                trade.set_custom_data(self.STAGE_SOLD.format(stage=1), True)
                return - ( trade.stake_amount * self.stage_1_sell_amount )
            elif not trade.get_custom_data(self.STAGE_SOLD.format(stage=2), default=False) and current_price_rate >= self.target_stage_2:
                self.logger.info(f"Price rise up bigger than {self.target_stage_2}, closing second target {self.stage_2_sell_amount}")
                trade.set_custom_data(self.STAGE_SOLD.format(stage=2), True)
                return - ( trade.stake_amount * self.stage_2_sell_amount )
            elif current_price_rate >= self.target_percent:
                return - trade.stake_amount
            else:
                return None
        except Exception as e:
            self.logger.info(f"Error occured during trade position adjustment: {str(e)}")
            return None