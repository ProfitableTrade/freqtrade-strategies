from freqtrade.strategy.interface import IStrategy
import talib.abstract as ta
from pandas import DataFrame

class CrossEMAStrategy(IStrategy):
    INTERFACE_VERSION = 2
    minimal_roi = {"0": 50}
    stoploss = -0.04

    # Параметри для плаваючого стоплоса
    trailing_stop = True
    trailing_stop_positive = 0.045  # 1%
    trailing_stop_positive_offset = 0.048  # 2%
    trailing_only_offset_is_reached = True


    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=28)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=48)
        
        stoch_rsi = ta.STOCHRSI(dataframe['close'], timeperiod=14, fastk_period=3, fastd_period=3)
        dataframe['stoch_rsi_k'] = stoch_rsi[0]  # fastk
        dataframe['stoch_rsi_d'] = stoch_rsi[1]  # fastd

        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['ema_fast'] > dataframe['ema_slow']) &
                (dataframe['stoch_rsi_k'] < 0.20)
            ),
            'buy'] = 1

        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['ema_fast'] < dataframe['ema_slow']) &
                (dataframe['stoch_rsi_k'] > 0.80)
            ),
            'sell'] = 1
        return dataframe
