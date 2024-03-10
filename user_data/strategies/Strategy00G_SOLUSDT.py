# --- Do not remove these libs ---
from freqtrade.strategy import IStrategy
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
from pandas import DataFrame
# --------------------------------

class Strategy00G_SOLUSDT(IStrategy):
    """
    Strategy 00G_SOLUSDT
    author@: Yurii Udaltsov + Claude (Anthropic)
    github@: https://github.com/freqtrade/freqtrade-strategies

    How to use it?
    > python3 ./freqtrade/main.py -s Strategy00G_SOLUSDT
    """

    INTERFACE_VERSION: int = 3

    # Оптимальний стоп-лосс або %max, розроблений для стратегії
    stoploss = -0.05

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

    # Цілі для частково закриття позиції та плаваючий стоп-лосс
    target_profit_1 = 0.015  # 1.5% profit
    target_profit_2 = 0.039  # 3.9% profit 
    target_profit_3 = 0.127  # 12.7% profit
    target_profit_4 = 0.195  # 19.5% profit

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
        dataframe['ema15'] = ta.EMA(dataframe, timeperiod=20)

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
        Generates sell signal based on EMA indicators
        A sell signal is generated when EMA 15 crosses below EMA 30
        """
        dataframe.loc[
            (
                qtpylib.crossed_below(dataframe['ema15'], dataframe['ema30'])
            ),
            'exit_long'] = 1

        return dataframe

    def custom_exit_signal(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Generates additional exit signals based on target profits and adjusts stoploss
        """
        # Get the entry price
        entry_price = dataframe.iloc[-1]['open']

        # Calculate target prices
        target_price_1 = entry_price * (1 + self.target_profit_1)
        target_price_2 = entry_price * (1 + self.target_profit_2)
        target_price_3 = entry_price * (1 + self.target_profit_3)
        target_price_4 = entry_price * (1 + self.target_profit_4)

        # Generate exit signals for target profits
        dataframe['exit_profit_1'] = 0.0
        dataframe['exit_profit_2'] = 0.0
        dataframe['exit_profit_3'] = 0.0
        dataframe['exit_profit_4'] = 0.0

        dataframe.loc[dataframe['close'] >= target_price_1, 'exit_profit_1'] = 1
        dataframe.loc[dataframe['close'] >= target_price_2, 'exit_profit_2'] = 1
        dataframe.loc[dataframe['close'] >= target_price_3, 'exit_profit_3'] = 1
        dataframe.loc[dataframe['close'] >= target_price_4, 'exit_profit_4'] = 1

        # Adjust stoploss based on target profits
        dataframe.loc[dataframe['close'] > target_price_1, 'stoploss'] = entry_price
        dataframe.loc[dataframe['close'] > target_price_2, 'stoploss'] = target_price_1
        dataframe.loc[dataframe['close'] > target_price_3, 'stoploss'] = target_price_2

        return dataframe

    def custom_exit(self, pair: str, trade: 'Trade', current_time: 'datetime', current_rate: float,
                    current_profit: float, **kwargs):
        """
        Custom exit for taking partial profits at target prices
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1]

        # Exit for target profits
        if last_candle['exit_profit_1'] == 1:
            amount = 0.2  # Sell 20% of the position
            self.execute_trade_exit(trade, amount, current_rate, 'exit_profit_1')

        if last_candle['exit_profit_2'] == 1:
            amount = 0.3  # Sell 30% of the remaining position
            self.execute_trade_exit(trade, amount, current_rate, 'exit_profit_2')

        if last_candle['exit_profit_3'] == 1:
            amount = 0.5  # Sell 50% of the remaining position
            self.execute_trade_exit(trade, amount, current_rate, 'exit_profit_3')

        if last_candle['exit_profit_4'] == 1:
            amount = 1.0  # Sell the remaining position
            self.execute_trade_exit(trade, amount, current_rate, 'exit_profit_4')