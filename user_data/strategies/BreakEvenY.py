from freqtrade.strategy import IStrategy
from freqtrade.vendor.qtpylib.indicators import crossed_above, crossed_below
from pandas import DataFrame

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

    def ema(self, dataframe: DataFrame, timeperiod: int) -> DataFrame:
        """
        Calculate EMA without using TA-Lib
        """
        k = 2 / (timeperiod + 1)
        dataframe['ema'] = dataframe['close'].ewm(span=timeperiod, adjust=False).mean()
        return dataframe['ema']

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Adds EMA 15 and EMA 30 indicators to the given DataFrame
        """
        # Calculate and add EMA 15
        dataframe['ema15'] = self.ema(dataframe, timeperiod=15)

        # Calculate and add EMA 30
        dataframe['ema30'] = self.ema(dataframe, timeperiod=30)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Generates buy signal based on EMA indicators
        """
        dataframe.loc[
            (
                crossed_above(dataframe['ema15'], dataframe['ema30'])
            ),
            'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Generates sell signal based on EMA indicators
        """
        dataframe.loc[
            (
                crossed_below(dataframe['ema15'], dataframe['ema30'])
            ),
            'exit_long'] = 1

        return dataframe
