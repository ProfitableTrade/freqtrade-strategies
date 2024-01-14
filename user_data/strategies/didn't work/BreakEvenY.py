from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame

class CustomEMAStrategy(IStrategy):
    """
    Custom EMA Strategy
    This is a simple strategy using EMA and Stochastic RSI without TA-Lib.
    """

    INTERFACE_VERSION = 2

    # Оптимальний стоп-лосс або %max, розроблений для стратегії
    stoploss = -0.05

    # Оптимальний таймфрейм для стратегії
    timeframe = '5m'

    # ROI table:
    minimal_roi = {
        "0": 0.01
    }

    # Trailing stop:
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02
    trailing_only_offset_is_reached = False

    def ema(self, series, timeperiod):
        """
        Calculate EMA without using TA-Lib
        """
        return series.ewm(span=timeperiod, adjust=False).mean()

    def stoch_rsi(self, series, timeperiod, fastk_period, fastd_period):
        """
        Calculate Stochastic RSI without using TA-Lib
        """
        delta = series.diff()
        dUp, dDown = delta.copy(), delta.copy()
        dUp[dUp < 0] = 0
        dDown[dDown > 0] = 0

        RolUp = dUp.rolling(window=timeperiod).mean()
        RolDown = dDown.abs().rolling(window=timeperiod).mean()
        RS = RolUp / RolDown
        rsi = 100.0 - (100.0 / (1.0 + RS))

        stochrsi = (rsi - rsi.rolling(window=timeperiod).min()) / (rsi.rolling(window=timeperiod).max() - rsi.rolling(window=timeperiod).min())
        fastk = stochrsi.rolling(window=fastk_period).mean()
        fastd = fastk.rolling(window=fastd_period).mean()

        return fastk, fastd

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Adds several different indicators to the given DataFrame
        """
        dataframe['ema_fast'] = self.ema(dataframe['close'], 28)
        dataframe['ema_slow'] = self.ema(dataframe['close'], 48)

        fastk, fastd = self.stoch_rsi(dataframe['close'], 14, 3, 3)
        dataframe['stoch_rsi_k'] = fastk
        dataframe['stoch_rsi_d'] = fastd

        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on indicators add buy signals
        """
        dataframe.loc[
            (
                (dataframe['ema_fast'] > dataframe['ema_slow']) &
                (dataframe['stoch_rsi_k'] < 0.20)
            ),
            'buy'] = 1

        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on indicators add sell signals
        """
        dataframe.loc[
            (
                (dataframe['ema_fast'] < dataframe['ema_slow']) &
                (dataframe['stoch_rsi_k'] > 0.80)
            ),
            'sell'] = 1

        return dataframe
