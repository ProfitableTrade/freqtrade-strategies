from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib

class Strategy00G_SOLUSDT_GPT(IStrategy):
    """
    Strategy 00G_SOLUSDT_GPT
    Author: Yurii Udaltsov
    This strategy uses EMA crossover for entry signals and implements dynamic profit targets for exits.
    """

    INTERFACE_VERSION: int = 3

    stoploss = -0.05
    timeframe = '30m'
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False

    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }

    # Define profit targets for the strategy
    profit_targets = [
        {'profit_percent': 0.015, 'sell_ratio': 0.2},
        {'profit_percent': 0.039, 'sell_ratio': 0.3},
        {'profit_percent': 0.127, 'sell_ratio': 0.5},
        {'profit_percent': 0.195, 'sell_ratio': 1.0},
    ]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['ema15'] = ta.EMA(dataframe, timeperiod=15)
        dataframe['ema30'] = ta.EMA(dataframe, timeperiod=30)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            qtpylib.crossed_above(dataframe['ema15'], dataframe['ema30']),
            'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            qtpylib.crossed_below(dataframe['ema15'], dataframe['ema30']),
            'exit_long'] = 1
        return dataframe

    def custom_sell(self, pair: str, trade: 'Trade', current_time: 'datetime', current_rate: float, current_profit: float, **kwargs) -> str:
        if trade.open_rate is None or trade.amount is None:
            return 'none'  # Safety check

        current_profit_percent = current_profit  # current_profit is already a percentage

        for i, target in enumerate(self.profit_targets):
            target_profit = target['profit_percent']
            if current_profit_percent >= target_profit:
                # Partial sell based on the target's sell_ratio
                # This needs to be handled by executing the sell order partially and adjusting the trade amount accordingly
                # Consider custom implementation to execute partial sell
                return f'custom_sell_target_{i+1}'

        return 'none'  # Return 'none' to indicate no custom sell at this point

    # Implement the custom_stoploss function if required, similar to custom_sell, to adjust the stop loss dynamically
