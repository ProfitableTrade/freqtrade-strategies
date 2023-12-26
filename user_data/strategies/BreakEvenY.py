from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta

class ModifiedBreakEven(IStrategy):
    INTERFACE_VERSION: int = 3

    # Встановлення ROI та стоп-лоссу з оригінальної стратегії BreakEven
    minimal_roi = {
        "0": 0.01,  # at least 1% at first
        "10": 0     # after 10min, everything goes
    }
    stoploss = -0.01

    # Встановлення таймфрейму
    timeframe = '5m'

    # Розрахунок індикаторів
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['ema20'] = ta.EMA(dataframe, timeperiod=20)
        dataframe['ema30'] = ta.EMA(dataframe, timeperiod=30)
        return dataframe

    # Логіка відкриття угод
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['ema20'] > dataframe['ema30']) &  # EMA 20 перетинає EMA 30 знизу вгору
                (dataframe['ema20'].shift(1) <= dataframe['ema30'].shift(1))  # Попереднє значення EMA 20 було нижче або рівне EMA 30
            ),
            'enter_long'] = 1
        return dataframe

    # Логіка закриття угод (застосовується ROI та стоп-лосс)
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Тут немає спеціальної логіки для виходу, оскільки вона здійснюється через ROI та стоп-лосс
        return dataframe
