# --- Do not remove these libs ---
from freqtrade.strategy import IStrategy
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
from pandas import DataFrame
# --------------------------------

class Strategy00_SL_ATOMUSDT(IStrategy):
    """
    Strategy 00
    author@: Yurii Udaltsov
    github@: https://github.com/freqtrade/freqtrade-strategies

    How to use it?
    > python3 ./freqtrade/main.py -s Strategy00
    """

    INTERFACE_VERSION: int = 3

    # Оптимальний стоп-лосс або %max, розроблений для стратегії
    stoploss = -0.035

    # Оптимальний таймфрейм для стратегії
    timeframe = '30m'

    # Налаштування трейлінг стоп-лосу
    trailing_stop = True  # Включення трейлінг стоп-лосу
    trailing_stop_positive = 0.035  # Трейлінг стоп активується, коли прибуток досягає 3,5%
    trailing_stop_positive_offset = 0.036  # Трейлінг стоп починає діяти, коли прибуток перевищує 3,6%
    trailing_only_offset_is_reached = True  # Трейлінг стоп активується тільки після досягнення offset

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
        # Calculate and add EMA 28
        dataframe['ema15'] = ta.EMA(dataframe, timeperiod=28)

        # Calculate and add EMA 48
        dataframe['ema30'] = ta.EMA(dataframe, timeperiod=48)

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
        Generates sell signal based on EMA indicators
        A sell signal is generated when EMA 15 crosses below EMA 30
        """
        dataframe.loc[
            (
                qtpylib.crossed_below(dataframe['ema15'], dataframe['ema30'])
            ),
            'exit_long'] = 1

        return dataframe
      