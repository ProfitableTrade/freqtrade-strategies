# --- Do not remove these libs ---
from freqtrade.strategy import IStrategy
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
from pandas import DataFrame
# --------------------------------

class Strategy00plus1(IStrategy):
    """
    Strategy 00 plus1
    author@: Yurii Udaltsov
    github@: https://github.com/freqtrade/freqtrade-strategies

    How to use it?
    > python3 ./freqtrade/main.py -s Strategy00
    """

    INTERFACE_VERSION: int = 3

    # Оптимальний стоп-лосс або %max, розроблений для стратегії
    stoploss = -0.08

    # Оптимальний таймфрейм для стратегії
    timeframe = '30m'

    # Trailing stop
    trailing_stop = False
    trailing_stop_positive = 0.5
    trailing_stop_positive_offset = 0.6

    # Process only new candles
    process_only_new_candles = True

    # Experimental parameters
    use_exit_signal = True
    exit_profit_only = False

    # Optional order type mapping
    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Adds EMA 15 and EMA 30 indicators to the given DataFrame
        """
        dataframe['ema15'] = ta.EMA(dataframe, timeperiod=15)
        dataframe['ema30'] = ta.EMA(dataframe, timeperiod=30)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Generates buy signal based on EMA indicators
        A buy signal is generated when EMA 15 crosses above EMA 30
        """
        dataframe.loc[
            (
                qtpylib.crossed_above(dataframe['ema15'], dataframe['ema30'])
            ),
            'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Modified exit logic to close the trade in steps based on profit percentage
        """
        # Перевірка, чи ціна зросла на 1.5%, 3%, 8%, 14%, та 16.5%
        profit = dataframe['close'] / dataframe['open'] - 1

        # Ціна зросла на 1.5%
        dataframe.loc[(profit >= 0.02), 'exit_long_50'] = 1  # Закриття 50% позиції

        # Ціна зросла на 3%
        dataframe.loc[(profit >= 0.1), 'exit_long_10'] = 1  # Закриття 10% позиції

        # Ціна зросла на 8%
        dataframe.loc[(profit >= 0.13), 'exit_long_10'] = 1  # Закриття ще 10% позиції

        # Ціна зросла на 14%
        dataframe.loc[(profit >= 0.18), 'exit_long_10'] = 1  # Закриття ще 10% позиції

        # Ціна зросла на 16.5%
        dataframe.loc[(profit >= 0.255), 'exit_long'] = 1  # Повне закриття позиції (100%)

        return dataframe
