# --- Do not remove these libs ---
import datetime
import logging
from typing import Optional, Tuple, Union
from freqtrade.strategy import IStrategy, informative
from pandas import DataFrame
from freqtrade.persistence import Trade
from freqtrade.strategy import stoploss_from_open
import talib.abstract as ta


class SettingsObject:
    bids_ask_delta: float
    depth: int
    volume_threshold: int
    
    def __init__(self, bids_ask_delta: float, depth: int, volume_threshold: int):
        self.bids_ask_delta = bids_ask_delta
        self.depth = depth
        self.volume_threshold = volume_threshold
        


class Strategy_Goal_Vidra_EMA(IStrategy):
    """
    Strategy_Goal_Vidra 
    author@: Yurii Udaltsov and Illia
    github@: https://github.com/freqtrade/freqtrade-strategies

    How to use it?
    > python3 ./freqtrade/main.py -s Strategy_Goal_Vidra_SOL
    """

    INTERFACE_VERSION: int = 3
    STAGE_SOLD: str = "stage_{stage}_sold"
    STAGE_BOUGHT: str = "stage_{stage}_bought"
    
    STRATEGY_SHEET_NAME = "DepthSpot"
    
    STRATEGY_SETTINGS = {
        "ATOM/USDT": SettingsObject(1.5, 15 , 3000),
        "ARB/USDT": SettingsObject(1.5, 15 , 50000),
        "NEAR/USDT": SettingsObject(1.5, 15 , 5000),
        "ADA/USDT": SettingsObject(1.5, 15 , 70000),
        "SHIB/USDT": SettingsObject(1.5, 15 , 2805611222),
        "LINK/USDT": SettingsObject(1.5, 15 , 3500),
        "LEVER/USDT": SettingsObject(1.5, 15 , 2408477),
        "AVAX/USDT": SettingsObject(1.5, 15 , 1200),
        "GALA/USDT": SettingsObject(1.5, 15 ,  1032702),
        "EOS/USDT": SettingsObject(1.5, 15 ,  60000),
        "INJ/USDT": SettingsObject(1.5, 15, 700),
        "POL/USDT": SettingsObject(1.5, 15 ,  95000),
        "DYDX/USDT": SettingsObject(1.5, 15 ,  22000),
        "SOL/USDT": SettingsObject(1.5, 15 ,  300),
        "SUI/USDT": SettingsObject(1.5, 15 ,  20000),
        "TIA/USDT": SettingsObject(1.5, 15 ,  8000),
        "WLD/USDT": SettingsObject(1.5, 15 ,  50000),
        "RENDER/USDT": SettingsObject(1.5, 15 ,  6400),
        "IO/USDT": SettingsObject(1.5, 15 ,  15000),
        "FIL/USDT": SettingsObject(1.5, 15 ,  20000),
        "ARKM/USDT": SettingsObject(1.5, 15 ,  20000),
        "STRK/USDT": SettingsObject(1.5, 15 ,  100000),
        "W/USDT": SettingsObject(1.5, 15 ,  200000),
        "ETH/USDT": SettingsObject(1.5, 15 ,  500),
        "DOT/USDT": SettingsObject(1.5, 15 ,  7650),
        "AEVO/USDT": SettingsObject(1.5, 15 ,  80000),
        "DOGS/USDT": SettingsObject(1.5, 15 ,  62000000),
        "MANA/USDT": SettingsObject(1.5, 15 ,  60000),
        "FLOW/USDT": SettingsObject(1.5, 15 ,  38000),
        "KAVA/USDT": SettingsObject(1.5, 15 ,  42000),
        "ILV/USDT": SettingsObject(1.5, 15 ,  550),
        "HOOK/USDT": SettingsObject(1.5, 15 ,  55000),
        "LOKA/USDT": SettingsObject(1.5, 15 ,  32000),
        "DOGE/USDT": SettingsObject(1.5, 15 ,  2280500),
        "PYTH/USDT": SettingsObject(1.5, 15 ,  85000),
        "BLUR/USDT": SettingsObject(1.5, 15 ,  100000),
        "HFT/USDT": SettingsObject(1.5, 15 ,  65000),
        "ENA/USDT": SettingsObject(1.5, 15 ,  95000),
        "OP/USDT": SettingsObject(1.5, 15 ,  19000),
        "LDO/USDT": SettingsObject(1.5, 15 ,  19000)
    }
    
    timeframe = "5m"
    
    position_adjustment_enable = True

    # Оптимальний стоп-лосс або %max, розроблений для стратегії
    stoploss = -0.06
    
    # Беззбитковість 
    use_custom_stoploss = True
    
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
    target_percent = 0.12
    
    target_stage_1 = 0.01
    target_stage_2 = 0.04
    target_stage_3 = 0.08
    
    stage_1_sell_amount = 0.1
    stage_2_sell_amount = 0.3
    stage_3_sell_amount = 0.3
    
    stoploss_correction = 0.002
    
    
    # Step buying (DCA) settings
    dca_levels = [-0.03]  # Levels for additional buy-ins
    dca_buy_amounts = [2]  # Buy amounts for each level

    
    def bot_start(self, **kwargs) -> None:
        self.logger = logging.getLogger(__name__)
     
    @informative('1h')
    def populate_indicators_1h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        
        dataframe['ema9'] = ta.EMA(dataframe['close'], timeperiod=9)

        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe
    
    @property
    def plot_config(self):
        plot_config = {}
        plot_config['main_plot'] = {}
        plot_config['subplots'] = {
            # Additional subplot EMA
            "EMA": {
                'ema9_1h': {'color': 'red'}
            }
        }

        return plot_config
        

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Get correct settings for pair
        settings = self.STRATEGY_SETTINGS[metadata['pair']]
        
        order_book = self.dp.orderbook(metadata['pair'], settings.depth + 1)

        depth_value = self.check_depth_of_market(metadata['pair'], order_book, settings.depth, settings.bids_ask_delta)
        large_orders_value = self.analyze_large_orders(metadata['pair'], order_book, settings.volume_threshold)
        volume_value = dataframe['volume'] > dataframe['volume'].shift(-1)
        close_value = dataframe['close'] > dataframe['close'].shift(-1)
        
        ema_value_crossed = dataframe['close'] > dataframe['ema9_1h'] 
        ema_value_raised = dataframe['ema9_1h'] > dataframe['ema9_1h'].shift(-1)
        
        
        self.logger.info(f"{metadata['pair']} Volume operations: \nTail:\n{dataframe['volume'].tail(15)}\nRaised:\n{volume_value.tail(15)}")
        
        self.logger.info(f"{metadata['pair']} Close operations: \nTail:\n{dataframe['close'].tail(15)}\nRaised:\n{close_value.tail(15)}")
        
        self.logger.info(f"{metadata['pair']} EMA operations: \nTail:\n{dataframe['ema9_1h'].tail(15)}\nCrossed:\n{ema_value_crossed.tail(15)}\nRaised:\n{ema_value_raised.tail(15)}")
        
        #self.logger.info(f"Depth check: {depth_value}, large orders check: {large_orders_value}, volume check: {volume_value.tail(5)}, close check: {close_value.tail(5)}")

        dataframe.loc[
            (depth_value) & (large_orders_value) & (volume_value) & (close_value) & (ema_value_crossed | ema_value_raised),
            'enter_long'] = 1

        return dataframe


    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        

        return dataframe
    
    def check_depth_of_market(self, pair, order_book, depth, delta, exit=False) -> bool:
        if len(order_book['bids']) < depth or len(order_book['asks']) < depth:
            return False
        
        total_bids = sum([bid[1] for bid in order_book['bids'][:depth]])
        total_asks = sum([ask[1] for ask in order_book['asks'][:depth]])
        
        self.logger.info(f"[{pair}] Analyzing depth of market... Results: total bids / total asks is {total_bids / total_asks}, configured delta is {delta}")
        
        if exit:
            return ( total_asks / total_bids ) > delta  
        else:
            return ( total_bids / total_asks ) > delta  

    def analyze_large_orders(self, pair, order_book, threshold) -> bool:
        large_orders = [order for order in order_book['bids'] if order[1] >= threshold] + \
                       [order for order in order_book['asks'] if order[1] >= threshold]

        self.logger.info(f"[{pair}] Analyzing large orders for threshold {threshold}, found {len(large_orders)}")
        
        return len(large_orders) > 0
    
    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float, after_fill: bool,
                        **kwargs) -> Optional[float]:
        try:
            
            if trade.get_custom_data(self.STAGE_SOLD.format(stage=1), default=False):
                stoploss_level = self.target_stage_1 - self.stoploss_correction
                #self.logger.info(f"Stoploss moved to {stoploss_level} due to first target reached")
                return stoploss_from_open(stoploss_level, current_profit, is_short=trade.is_short, leverage=trade.leverage)
            elif trade.get_custom_data(self.STAGE_SOLD.format(stage=2), default=False):
                stoploss_level = self.target_stage_2 - self.stoploss_correction
                #self.logger.info(f"Stoploss moved to {stoploss_level} due to second target reached")
                return stoploss_from_open(stoploss_level, current_profit, is_short=trade.is_short, leverage=trade.leverage)

            return None
        except Exception as e:
            self.logger.info(f"[{trade.pair}] Error occured during custom stoploss definition: {str(e)}")
            return None
    
    def adjust_trade_position(self, trade: Trade, current_time: datetime,
                              current_rate: float, current_profit: float,
                              min_stake: Optional[float], max_stake: float,
                              current_entry_rate: float, current_exit_rate: float,
                              current_entry_profit: float, current_exit_profit: float,
                              **kwargs
                              ) -> Union[Optional[float], Tuple[Optional[float], Optional[str]]]:
        try:
            
            current_price_rate = current_rate / trade.open_rate - 1
            #self.logger.info(f"[{trade.pair}] Check for goal to be closed, price rate {current_price_rate}")
            
            # Check if DCA levels are hit
            for level, amount in zip(self.dca_levels, self.dca_buy_amounts):
                if not trade.get_custom_data(self.STAGE_BOUGHT.format(stage=self.dca_levels.index(level)), default=False) and current_price_rate <= level:
                    self.logger.info(f"[{trade.pair}] DCA level {level} reached, buying {amount * 100}% more")
                    trade.set_custom_data(self.STAGE_BOUGHT.format(stage=self.dca_levels.index(level)), True)
                    return amount * trade.stake_amount

            if not trade.get_custom_data(self.STAGE_SOLD.format(stage=1), default=False) and current_price_rate >= self.target_stage_1:
                self.logger.info(f"[{trade.pair}] Price rise up bigger than {self.target_stage_1}, closing first target {self.stage_1_sell_amount}")
                trade.set_custom_data(self.STAGE_SOLD.format(stage=1), True)
                return - ( trade.stake_amount * self.stage_1_sell_amount )
            elif not trade.get_custom_data(self.STAGE_SOLD.format(stage=2), default=False) and current_price_rate >= self.target_stage_2:
                self.logger.info(f"[{trade.pair}] Price rise up bigger than {self.target_stage_2}, closing second target {self.stage_2_sell_amount}")
                trade.set_custom_data(self.STAGE_SOLD.format(stage=2), True)
                return - ( trade.stake_amount * self.stage_2_sell_amount )
            elif not trade.get_custom_data(self.STAGE_SOLD.format(stage=3), default=False) and current_price_rate >= self.target_stage_3:
                self.logger.info(f"[{trade.pair}] Price rise up bigger than {self.target_stage_3}, closing second target {self.stage_3_sell_amount}")
                trade.set_custom_data(self.STAGE_SOLD.format(stage=3), True)
                return - ( trade.stake_amount * self.stage_3_sell_amount )
            elif current_price_rate >= self.target_percent:
                return - trade.stake_amount
            else:
                return None
        except Exception as e:
            self.logger.info(f"[{trade.pair}] Error occured during trade position adjustment: {str(e)}")
            return None