from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame

class Strategy_EMACrossoverStopLoss(IStrategy):
    
    INTERFACE_VERSION: int = 3

    # Stoploss
    stoploss = -0.05  # Fixed stop-loss of 5%

    # Trailing stoploss (not used in this strategy)
    trailing_stop = False

    # Timeframe for the strategy
    timeframe = '4h'

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Add EMA indicators to the dataframe.
        """
        # Calculate EMAs
        dataframe['ema_20'] = dataframe['close'].ewm(span=20, adjust=False).mean()
        dataframe['ema_30'] = dataframe['close'].ewm(span=30, adjust=False).mean()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate the entry signals.
        """
        # Open a long position when EMA 20 > EMA 30
        dataframe.loc[
            (dataframe['ema_20'] > dataframe['ema_30']),
            'enter_long'
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate the exit signals.
        """
        # Exit when EMA 20 < EMA 30
        dataframe.loc[
            (dataframe['ema_20'] < dataframe['ema_30']),
            'exit_long'
        ] = 1

        return dataframe
