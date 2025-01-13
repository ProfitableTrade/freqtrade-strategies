from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame

class Strategy_BollingerBands(IStrategy):
    
    INTERFACE_VERSION: int = 3
    
    # Stoploss
    stoploss = -0.15  # Placeholder (can be ignored when using fixed or trailing SL logic)

    # Trailing stoploss
    trailing_stop = False  # Set True if you want native trailing stop

    # Timeframe for the strategy
    timeframe = '1h'

    # Bollinger Bands parameters
    bb_length = 17
    bb_mult = 2.0

    # Trailing Stop settings
    use_trailing = False
    trailing_percentage = 10.0  # % from the local max

    # Fixed Stop-Loss settings
    use_fixed_sl = True
    fixed_sl_percentage = 4.0  # % from the entry price

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Add Bollinger Bands and other indicators to the dataframe.
        """
        # Calculate Bollinger Bands
        dataframe['bb_basis'] = dataframe['close'].rolling(window=self.bb_length).mean()
        dataframe['bb_stddev'] = dataframe['close'].rolling(window=self.bb_length).std()
        dataframe['bb_upper'] = dataframe['bb_basis'] + (self.bb_mult * dataframe['bb_stddev'])
        dataframe['bb_lower'] = dataframe['bb_basis'] - (self.bb_mult * dataframe['bb_stddev'])

        # Record the highest price for trailing stop
        dataframe['highest_price'] = dataframe['close'].cummax()

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate the entry signals.
        """
        # Check for long condition: close > bb_upper within the time range
        dataframe.loc[
            (dataframe['close'] > dataframe['bb_upper']),
            'enter_long'
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate the exit signals.
        """
        # Check for flat condition: close < bb_lower within the time range
        dataframe.loc[
            (dataframe['close'] < dataframe['bb_lower']),
            'exit_long'
        ] = 1

        # Manual trailing stop logic
        if self.use_trailing:
            trailing_stop_level = dataframe['highest_price'] * (1 - self.trailing_percentage / 100)
            dataframe.loc[
                (dataframe['close'] < trailing_stop_level),
                'exit_long'
            ] = 1

        # Fixed stop-loss logic
        if self.use_fixed_sl:
            dataframe['entry_price'] = dataframe['close'].shift(1)  # Assuming entry price is the previous close
            stop_loss_level = dataframe['entry_price'] * (1 - self.fixed_sl_percentage / 100)
            dataframe.loc[
                (dataframe['close'] < stop_loss_level),
                'exit_long'
            ] = 1

        return dataframe
