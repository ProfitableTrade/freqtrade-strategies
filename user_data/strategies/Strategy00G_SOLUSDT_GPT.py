from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
import talib.abstract as ta
from freqtrade.persistence import Trade
from datetime import datetime

class Strategy00G_SOLUSDT_GPT(IStrategy):
    """
    Strategy 00G_SOLUSDT_GPT
    Author: Yurii Udaltsov
    Description: This strategy uses EMA crossover for entry and dynamic profit targets with adjustable percentages for exits.
    """

    INTERFACE_VERSION: int = 3

    stoploss = -0.05  # Initial stop loss

    timeframe = '30m'

    # Dynamic trailing stop loss is not initially enabled
    trailing_stop = True
    trailing_stop_positive = 0.0
    trailing_stop_positive_offset = 0.01  # Trigger trailing stop as soon as in profit

    process_only_new_candles = True

    use_exit_signal = True
    exit_profit_only = False

    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }

    # Define custom profit targets and the percentage of the trade to sell at each target
    profit_targets = [
        {'profit_percent': 0.015, 'sell_ratio': 0.2},
        {'profit_percent': 0.039, 'sell_ratio': 0.3},
        {'profit_percent': 0.127, 'sell_ratio': 0.5},
        {'profit_percent': 0.195, 'sell_ratio': 1.0},
    ]

    def informative_pairs(self):
        """
        Define additional, informative pair/interval combinations to be cached from the exchange.
        These pairs are non-tradeable, but can be used to analyze market conditions.
        """
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Add necessary indicators here, for example, EMA
        """
        dataframe['ema15'] = ta.EMA(dataframe, timeperiod=15)
        dataframe['ema30'] = ta.EMA(dataframe, timeperiod=30)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Enter long condition - EMA 15 crosses above EMA 30
        """
        dataframe.loc[
            (
                ta.CROSSOVER(dataframe['ema15'], dataframe['ema30'])
            ),
            'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Exit long condition - Will be overridden by custom_stoploss function
        """
        dataframe['exit_long'] = 0
        return dataframe

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: 'datetime', current_rate: float, current_profit: float, **kwargs) -> float:
        """
        Dynamic stop loss strategy that adjusts stop loss levels as the trade progresses through defined profit targets.
        """

        # Check if any of the profit targets have been hit. If so, adjust the stop loss accordingly.
        for target in self.profit_targets:
            target_profit = trade.open_rate * (1 + target['profit_percent'])
            if current_rate >= target_profit:
                # Calculate new stop loss relative to the current price, not to exceed the initial stop loss
                new_stop_loss_rate = current_rate * (1 + self.stoploss)
                new_stop_loss = max(self.stoploss, 1 - new_stop_loss_rate / trade.open_rate)
                return new_stop_loss

        # If no targets have been hit, return the initial stop loss
        return self.stoploss

    def custom_sell(self, pair: str, trade: 'Trade', current_time: 'datetime', current_rate: float, current_profit: float, **kwargs) -> str:
        """
        Custom sell logic to be used for selling at the defined profit targets.
        """

        # Check each profit target to see if it has been hit and sell a portion of the trade accordingly
        for i, target in enumerate(self.profit_targets):
            target_profit = trade.open_rate * (1 + target['profit_percent'])
            if current_rate >= target_profit and trade.custom_info.get(f'target{i+1}_hit', False) is False:
                # Mark this target as hit
                trade.custom_info[f'target{i+1}_hit'] = True
                # Return a sell reason tag including which target was hit
                return f'sell_target{i+1}_hit'

        # Default sell reason if none of the targets have been hit
        return 'none'
