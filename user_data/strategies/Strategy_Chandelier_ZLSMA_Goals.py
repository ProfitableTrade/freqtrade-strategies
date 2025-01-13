# --- Do not remove these libs ---
import logging
import datetime
from typing import Optional, Tuple, Union
from freqtrade.strategy import IStrategy
from freqtrade.strategy import IntParameter, DecimalParameter, BooleanParameter
from pandas import DataFrame
from freqtrade.persistence import Trade
from freqtrade.strategy import stoploss_from_open
import talib.abstract as ta
import numpy as np
        


class Strategy_Chandelier_ZLSMA_Goals(IStrategy):
    """
    Strategy_Chandelier_ZLSMA_Goals 
    author@: Illia
    github@: https://github.com/freqtrade/freqtrade-strategies

    How to use it?
    > python3 ./freqtrade/main.py -s Strategy_Chandelier_ZLSMA_Goals
    """

    INTERFACE_VERSION: int = 3
    
    STAGE_SOLD: str = "stage_{stage}_sold"
    
    
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
    
    atr_period = IntParameter(10, 30, default=22, space="buy")
    atr_multiplier = DecimalParameter(1.0, 5.0, default=3.0, space="buy")
    zlsma_length = IntParameter(10, 50, default=32, space="buy")
    zlsma_offset = IntParameter(0, 10, default=0, space="buy")
    use_close_price = BooleanParameter(default=True, space="buy")

    
    def bot_start(self, **kwargs) -> None:
        self.logger = logging.getLogger(__name__)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # ATR Calculation
        dataframe['atr'] = ta.ATR(dataframe['high'], dataframe['low'], dataframe['close'], timeperiod=self.atr_period.value)
        dataframe['atr_multiplier'] = dataframe['atr'] * self.atr_multiplier.value

        # Chandelier Exit Calculations
        if self.use_close_price.value:
            dataframe['long_stop'] = dataframe['close'].rolling(window=self.atr_period.value).max() - dataframe['atr_multiplier']
            dataframe['short_stop'] = dataframe['close'].rolling(window=self.atr_period.value).min() + dataframe['atr_multiplier']
        else:
            dataframe['long_stop'] = dataframe['high'].rolling(window=self.atr_period.value).max() - dataframe['atr_multiplier']
            dataframe['short_stop'] = dataframe['low'].rolling(window=self.atr_period.value).min() + dataframe['atr_multiplier']

        # Update previous stop levels
        dataframe['long_stop_prev'] = dataframe['long_stop'].shift(1).fillna(dataframe['long_stop'])
        dataframe['short_stop_prev'] = dataframe['short_stop'].shift(1).fillna(dataframe['short_stop'])

        dataframe['long_stop'] = np.where(
            dataframe['close'].shift(1) > dataframe['long_stop_prev'],
            np.maximum(dataframe['long_stop'], dataframe['long_stop_prev']),
            dataframe['long_stop']
        )
        dataframe['short_stop'] = np.where(
            dataframe['close'].shift(1) < dataframe['short_stop_prev'],
            np.minimum(dataframe['short_stop'], dataframe['short_stop_prev']),
            dataframe['short_stop']
        )

        # ZLSMA Calculation
        dataframe['zlsma'] = ta.LINEARREG(dataframe['close'], timeperiod=self.zlsma_length.value)
        dataframe['lsma2'] = ta.LINEARREG(dataframe['zlsma'], timeperiod=self.zlsma_length.value)
        dataframe['eq'] = dataframe['zlsma'] - dataframe['lsma2']
        dataframe['zlsma_final'] = dataframe['zlsma'] + dataframe['eq']

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Buy condition
        dataframe.loc[
            (dataframe['close'] > dataframe['zlsma_final']) &
            (dataframe['close'] > dataframe['short_stop_prev']),
            'enter_long'] = 1

        return dataframe


    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
         # Long exit
        # dataframe.loc[
        #     (dataframe['close'] < dataframe['zlsma_final']),
        #     'exit_long'] = 1

        return dataframe
    
    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float, after_fill: bool,
                        **kwargs) -> Optional[float]:
        try:
            
            if trade.get_custom_data(self.STAGE_SOLD.format(stage=1), default=False):
                return stoploss_from_open(self.stoploss_correction, current_profit, is_short=trade.is_short, leverage=trade.leverage)
            elif trade.get_custom_data(self.STAGE_SOLD.format(stage=2), default=False):
                return stoploss_from_open(self.target_stage_1, current_profit, is_short=trade.is_short, leverage=trade.leverage)
            elif trade.get_custom_data(self.STAGE_SOLD.format(stage=3), default=False):
                return stoploss_from_open(self.target_stage_2, current_profit, is_short=trade.is_short, leverage=trade.leverage)

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
    
    