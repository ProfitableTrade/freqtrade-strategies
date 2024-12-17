# --- Do not remove these libs ---
import logging
from freqtrade.strategy import IStrategy
from freqtrade.strategy import IntParameter, DecimalParameter, BooleanParameter
from pandas import DataFrame
import talib.abstract as ta
import numpy as np
        


class Strategy_Chandelier_ZLSMA(IStrategy):
    """
    Strategy_Chandelier_ZLSMA 
    author@: Illia
    github@: https://github.com/freqtrade/freqtrade-strategies

    How to use it?
    > python3 ./freqtrade/main.py -s Strategy_Chandelier_ZLSMA
    """

    INTERFACE_VERSION: int = 3

    # Оптимальний стоп-лосс або %max, розроблений для стратегії
    stoploss = -0.06

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
    
    atr_period = IntParameter(10, 30, default=22)
    atr_multiplier = DecimalParameter(1.0, 5.0, default=3.0)
    zlsma_length = IntParameter(10, 50, default=32)
    zlsma_offset = IntParameter(0, 10, default=0)
    use_close_price = BooleanParameter(default=True)

    
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

        # Sell condition (short)
        # dataframe.loc[
        #     (dataframe['close'] < dataframe['zlsma_final']) &
        #     (dataframe['close'] < dataframe['long_stop_prev']),
        #     'enter_short'] = 1

        return dataframe


    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
         # Long exit
        dataframe.loc[
            (dataframe['close'] < dataframe['zlsma_final']),
            'exit_long'] = 1

        # Short exit
        # dataframe.loc[
        #     (dataframe['close'] > dataframe['zlsma_final']),
        #     'exit_short'] = 1

        return dataframe
    
    