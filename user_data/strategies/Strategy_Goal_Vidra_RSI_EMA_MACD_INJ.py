# --- Do not remove these libs ---
import datetime
import logging
from typing import Optional, Tuple, Union
from freqtrade.strategy import IStrategy
from pandas import DataFrame
from freqtrade.persistence import Trade
import talib.abstract as ta


class SettingsObject:
    bids_ask_delta: float
    depth: int
    volume_threshold: int

    def __init__(self, bids_ask_delta: float, depth: int, volume_threshold: int):
        self.bids_ask_delta = bids_ask_delta
        self.depth = depth
        self.volume_threshold = volume_threshold


class Strategy_Goal_Vidra_RSI_Trend(IStrategy):
    """
    Strategy_Goal_Vidra_RSI_Trend
    author@: Yurii Udaltsov and Illia, modified by Assistant
    github@: https://github.com/freqtrade/freqtrade-strategies

    This strategy avoids buying during downtrends and trades only in uptrends or flat markets.
    """

    INTERFACE_VERSION: int = 3
    BE_ACTIVATED: str = "be_activated"
    STAGE_SOLD: str = "stage_{stage}_sold"
    STAGE_BOUGHT: str = "stage_{stage}_bought"

    STRATEGY_SHEET_NAME = "DepthSpot"

    STRATEGY_SETTINGS = {
        "5m": SettingsObject(1.3, 15, 500),
        "30m": SettingsObject(1.3, 15, 1000)
    }

    position_adjustment_enable = True

    # Оптимальний стоп-лосс або %max, розроблений для стратегії
    stoploss = -0.04  # Зменшено стоп-лосс до -4%

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

    # Settings for target reaching logic
    target_percent = 0.08

    target_stage_1 = 0.02
    target_stage_2 = 0.04

    stage_1_sell_amount = 0.3  # Збільшено частку для першого виходу
    stage_2_sell_amount = 0.4  # Збільшено частку для другого виходу

    # Step buying (DCA) settings
    dca_levels = [-0.02, -0.035]  # Зменшено кількість DCA рівнів
    dca_buy_amounts = [0.2, 0.2]  # Відповідні обсяги покупок

    rsi_buy_threshold = 35  # Порогове значення для покупки по RSI
    rsi_sell_threshold = 70  # Порогове значення для продажу по RSI

    # Додані параметри індикаторів
    ema_short_period = 50
    ema_long_period = 200
    macd_fast_period = 12
    macd_slow_period = 26
    macd_signal_period = 9
    adx_period = 14
    adx_threshold = 20  # Порогове значення ADX для визначення тренду

    def bot_start(self, **kwargs) -> None:
        self.logger = logging.getLogger(__name__)

        self.settings = self.STRATEGY_SETTINGS[self.timeframe]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)

        # EMA
        dataframe['ema_short'] = ta.EMA(dataframe, timeperiod=self.ema_short_period)
        dataframe['ema_long'] = ta.EMA(dataframe, timeperiod=self.ema_long_period)

        # MACD
        macd = ta.MACD(
            dataframe,
            fastperiod=self.macd_fast_period,
            slowperiod=self.macd_slow_period,
            signalperiod=self.macd_signal_period
        )
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']

        # ADX
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=self.adx_period)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Entry conditions with trend filters.
        """

        # Фільтри тренду
        trend_condition = (
            (dataframe['close'] > dataframe['ema_long']) &  # Ціна вище довгострокової EMA
            (dataframe['ema_short'] > dataframe['ema_long']) &  # EMA коротка вище довгої
            (dataframe['macd'] > dataframe['macdsignal']) &  # MACD вище сигнальної лінії
            (dataframe['adx'] > self.adx_threshold)  # Сильний тренд
        )

        order_book = self.dp.orderbook(metadata['pair'], self.settings.depth + 1)

        depth_value = self.check_depth_of_market(order_book, self.settings.depth, self.settings.bids_ask_delta)
        large_orders_value = self.analyze_large_orders(order_book, self.settings.volume_threshold)
        volume_value = dataframe['volume'] > dataframe['volume'].shift(1)
        close_value = dataframe['close'] < dataframe['close'].shift(1)
        rsi_buy_condition = dataframe['rsi'] < self.rsi_buy_threshold

        # Об'єднання всіх умов
        dataframe.loc[
            trend_condition &
            depth_value &
            large_orders_value &
            volume_value &
            close_value &
            rsi_buy_condition,
            'enter_long'] = 1

        # Логування
        self.logger.info(f"Entry conditions for {metadata['pair']} at {dataframe['date'].iloc[-1]}:")
        self.logger.info(f"Trend condition: {trend_condition.iloc[-1]}")
        self.logger.info(f"Depth check: {depth_value}, Large orders: {large_orders_value}")
        self.logger.info(f"Volume increasing: {volume_value.iloc[-1]}, Price decreasing: {close_value.iloc[-1]}")
        self.logger.info(f"RSI value: {dataframe['rsi'].iloc[-1]}")

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Умови виходу при зміні тренду або перепроданості
        exit_condition = (
            (dataframe['rsi'] > self.rsi_sell_threshold) |
            (dataframe['close'] < dataframe['ema_long']) |  # Ціна опустилася нижче довгострокової EMA
            (dataframe['macd'] < dataframe['macdsignal'])  # MACD нижче сигнальної лінії
        )

        dataframe.loc[exit_condition, 'exit_long'] = 1

        # Логування
        self.logger.info(f"Exit conditions for {metadata['pair']} at {dataframe['date'].iloc[-1]}:")
        self.logger.info(f"Exit condition met: {exit_condition.iloc[-1]}")
        self.logger.info(f"RSI value: {dataframe['rsi'].iloc[-1]}")

        return dataframe

    def check_depth_of_market(self, order_book, depth, delta, exit=False) -> bool:
        if len(order_book['bids']) < depth or len(order_book['asks']) < depth:
            return False

        total_bids = sum([bid[1] for bid in order_book['bids'][:depth]])
        total_asks = sum([ask[1] for ask in order_book['asks'][:depth]])

        ratio = total_bids / total_asks if total_asks != 0 else 0
        self.logger.info(f"Analyzing depth of market... Total bids/asks ratio: {ratio}, Configured delta: {delta}")

        if exit:
            return (total_asks / total_bids) > delta
        else:
            return ratio > delta

    def analyze_large_orders(self, order_book, threshold) -> bool:
        large_bids = [order for order in order_book['bids'] if order[1] >= threshold]
        large_asks = [order for order in order_book['asks'] if order[1] >= threshold]
        large_orders = large_bids + large_asks

        self.logger.info(f"Analyzing large orders for threshold {threshold}, found {len(large_orders)} large orders")

        return len(large_orders) > 0

    def adjust_trade_position(self, trade: Trade, current_time: datetime.datetime,
                              current_rate: float, current_profit: float,
                              min_stake: Optional[float], max_stake: float,
                              current_entry_rate: float, current_exit_rate: float,
                              current_entry_profit: float, current_exit_profit: float,
                              **kwargs
                              ) -> Union[Optional[float], Tuple[Optional[float], Optional[str]]]:
        try:
            current_price_rate = current_rate / trade.open_rate - 1
            self.logger.info(f"Adjusting trade position for {trade.pair} at {current_time}")
            self.logger.info(f"Current price rate: {current_price_rate:.4f}, Current profit: {current_profit:.4f}")

            # Check if DCA levels are hit
            for level, amount in zip(self.dca_levels, self.dca_buy_amounts):
                stage = self.dca_levels.index(level)
                if not trade.get_custom_value(self.STAGE_BOUGHT.format(stage=stage), default=False) and current_price_rate <= level:
                    self.logger.info(f"DCA level {level} reached, buying additional {amount * 100}% of initial stake")
                    trade.set_custom_value(self.STAGE_BOUGHT.format(stage=stage), True)
                    return amount * trade.stake_amount

            # Check for staged sells
            if not trade.get_custom_value(self.STAGE_SOLD.format(stage=1), default=False) and current_price_rate >= self.target_stage_1:
                self.logger.info(f"Target stage 1 reached at {self.target_stage_1}, selling {self.stage_1_sell_amount * 100}% of position")
                trade.set_custom_value(self.STAGE_SOLD.format(stage=1), True)
                return - (trade.amount * self.stage_1_sell_amount)
            elif not trade.get_custom_value(self.STAGE_SOLD.format(stage=2), default=False) and current_price_rate >= self.target_stage_2:
                self.logger.info(f"Target stage 2 reached at {self.target_stage_2}, selling {self.stage_2_sell_amount * 100}% of position")
                trade.set_custom_value(self.STAGE_SOLD.format(stage=2), True)
                return - (trade.amount * self.stage_2_sell_amount)
            elif current_price_rate >= self.target_percent:
                self.logger.info(f"Final target reached at {self.target_percent}, closing remaining position")
                return -trade.amount
            else:
                return None
        except Exception as e:
            self.logger.error(f"Error occurred during trade position adjustment: {str(e)}")
            return None
