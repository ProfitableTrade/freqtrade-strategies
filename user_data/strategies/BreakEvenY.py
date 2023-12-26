from freqtrade.strategy import IStrategy
from pandas import DataFrame
import numpy as np

class Strategy00(IStrategy):
    """
    Strategy 00
    author@: Yurii Udaltsov
    github@: https://github.com/freqtrade/freqtrade-strategies

    How to use it?
    > python3 ./freqtrade/main.py -s Strategy00
    """

    INTERFACE_VERSION: int = 3

    # Оптимальний стоп-лосс або %max, розроблений для стратегії
    stoploss = -0.03

    # Оптимальний таймфрейм для стратегії
    timeframe = '5m'

    # Trailing stoploss
    trailing_stop = False
    trailing_stop_positive = 0.5
    trailing_stop_positive_offset = 0.6

    # Запускати "populate_indicators" тільки для нової свічки
    process_only_new_candles = True

    # Експериментальні параметри
    use_exit_signal = True
    exit_profit_only = False

    # Optional order type mapping
    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }

    def ema(self, series: DataFrame, timeperiod: int) -> DataFrame:
        """
        Calculate EMA without using TA-Lib
        """
        return series.ewm(span=timeperiod, adjust=False).mean()

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Adds EMA 15 and EMA 30 indicators to the given DataFrame
        """
        dataframe['ema15'] = self.ema(dataframe['close'], timeperiod=15)
        dataframe['ema30'] = self.ema(dataframe['close'], timeperiod=30)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Generates buy signal based on EMA indicators
        """
        dataframe.loc[
            (
                (dataframe['ema15'] > dataframe['ema30']) & 
                (dataframe['ema15'].shift(1) <= dataframe['ema30'].shift(1))
            ),
            'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Generates sell signal based on EMA indicators
        """
        dataframe.loc[
            (
                (dataframe['ema15'] < dataframe['ema30']) & 
                (dataframe['ema15'].shift(1) >= dataframe['ema30'].shift(1))
            ),
            'exit_long'] = 1

        return dataframe
