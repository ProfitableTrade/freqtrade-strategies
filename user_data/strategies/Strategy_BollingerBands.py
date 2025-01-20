from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
import freqtrade.vendor.qtpylib.indicators as qtpylib

class Strategy_BollingerBands(IStrategy):
    
    INTERFACE_VERSION: int = 3
    
    # Stoploss
    stoploss = -0.05  # Placeholder (can be ignored when using fixed or trailing SL logic)

    # Trailing stoploss
    trailing_stop = False  # Set True if you want native trailing stop

    # Timeframe for the strategy
    timeframe = '1h'

    # Bollinger Bands parameters
    bb_length = 17
    bb_mult = 2.0

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Add Bollinger Bands and other indicators to the dataframe.
        """
        # Calculate Bollinger Bands
        
        bollinger = qtpylib.bollinger_bands(dataframe['close'], window=self.bb_length, stds=self.bb_mult)
        dataframe['bb_lowerband'] = bollinger['lower']
        dataframe['bb_upperband'] = bollinger['upper']
        dataframe['bb_middleband'] = bollinger['mid']

        # Record the highest price for trailing stop
        dataframe['highest_price'] = dataframe['close'].cummax()

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate the entry signals.
        """
        # Check for long condition: close > bb_upper within the time range
        dataframe.loc[
            (dataframe['close'] < dataframe['bb_lowerband']),
            'enter_long'
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate the exit signals.
        """
        # Check for flat condition: close < bb_lower within the time range
        dataframe.loc[
            (dataframe['close'] > dataframe['bb_upperband']),
            'exit_long'
        ] = 1

        return dataframe
