# --- Do not remove these libs ---
from freqtrade.strategy import IStrategy
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
from pandas import DataFrame
# --------------------------------

class Strategy00plus(IStrategy):
    """
    Strategy 00 plus
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

    # trailing stoploss або змінний стоплосс.  
    trailing_stop = False
    trailing_stop_positive = 0.5
    trailing_stop_positive_offset = 0.6

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

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Adds EMA 15 and EMA 30 indicators to the given DataFrame
        """
        # Calculate and add EMA 15
        dataframe['ema15'] = ta.EMA(dataframe, timeperiod=15)

        # Calculate and add EMA 30
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
        # Відслідковуємо, коли ціна зросла на 1%, 2%, та 3% від моменту входу в угоду
        # Тут може знадобитися додаткова логіка для точного відслідковування ціни входу в угоду
        # Припускаємо, що 'open' - це ціна входу в угоду

        # Ціна зросла на 1%
        dataframe.loc[
            (
                (dataframe['close'] / dataframe['open'] - 1) >= 0.01
            ),
            'exit_long_50'] = 1  # Закриття 50% позиції

        # Ціна зросла на 2%
        dataframe.loc[
            (
                (dataframe['close'] / dataframe['open'] - 1) >= 0.025
            ),
            'exit_long_25'] = 1  # Закриття ще 25% позиції

        # Ціна зросла на 3%
        dataframe.loc[
            (
                (dataframe['close'] / dataframe['open'] - 1) >= 0.04
            ),
            'exit_long'] = 1  # Повне закриття позиції

        return dataframe
