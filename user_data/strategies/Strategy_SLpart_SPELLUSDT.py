# --- Do not remove these libs ---
import datetime
from typing import Optional, Tuple, Union
from freqtrade.strategy import IStrategy
from freqtrade.persistence import Trade
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
from pandas import DataFrame
import logging

# --------------------------------

class Strategy_SLpart_SPELLUSDT(IStrategy):
    """
    Strategy 00
    author@: Yurii Udaltsov
    github@: https://github.com/freqtrade/freqtrade-strategies

    How to use it?
    > python3 ./freqtrade/main.py -s Strategy00
    """

    INTERFACE_VERSION: int = 3
    BEST_PRICE_KEY: str = "best_price"
    PL_SELL_HALF_KEY: str = "pl_sell_half"
    PL_SELL_3_4_KEY: str = "pl_sell_3_4"
    
    position_adjustment_enable = True

    # Оптимальний стоп-лосс або %max, розроблений для стратегії
    stoploss = -0.0125
    
    # TODO: Change for on start callback with ENV provision
    pl = 0.025

    # Оптимальний таймфрейм для стратегії
    timeframe = '30m'

    # Налаштування трейлінг стоп-лосу
    trailing_stop = True  # Включення трейлінг стоп-лосу
    trailing_stop_positive = 0.05  # Трейлінг стоп активується, коли прибуток досягає 3,3%
    # trailing_stop_positive_offset = 0.035  # Трейлінг стоп починає діяти, коли прибуток перевищує 3,5%
    # trailing_only_offset_is_reached = True  # Трейлінг стоп активується тільки після досягнення offset

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
    
    
    def bot_start(self, **kwargs) -> None:
        self.logger = logging.getLogger(__name__)

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
    
    def adjust_trade_position(self, trade: Trade, current_time: datetime,
                              current_rate: float, current_profit: float,
                              min_stake: Optional[float], max_stake: float,
                              current_entry_rate: float, current_exit_rate: float,
                              current_entry_profit: float, current_exit_profit: float,
                              **kwargs
                              ) -> Union[Optional[float], Tuple[Optional[float], Optional[str]]]:
        best_price = trade.get_custom_data(self.BEST_PRICE_KEY, default=0)
        half_closed = trade.get_custom_data(self.PL_SELL_HALF_KEY, default=False)
        closed_3_4 = trade.get_custom_data(self.PL_SELL_3_4_KEY, default=False)
        
        if not best_price:
            best_price = current_rate
            trade.set_custom_data(self.BEST_PRICE_KEY, best_price)
            return None
        
        profit_loss = 0
        
        if trade.trade_direction == "long":
            if current_rate > best_price:
                trade.set_custom_data(self.BEST_PRICE_KEY, current_rate)
                if half_closed:
                    trade.set_custom_data(self.PL_SELL_HALF_KEY, False)
                if closed_3_4:
                    trade.set_custom_data(self.PL_SELL_3_4_KEY, False)
                return None
            else:
                profit_loss = 1 - current_rate / best_price
        elif trade.trade_direction == "short":
            if current_rate < best_price:
                trade.set_custom_data(self.BEST_PRICE_KEY, current_rate)
                if half_closed:
                    trade.set_custom_data(self.PL_SELL_HALF_KEY, False)
                if closed_3_4:
                    trade.set_custom_data(self.PL_SELL_3_4_KEY, False)
                return None
            else:
                profit_loss = 1 - best_price / current_rate     
        else:
            return None
        
                
        if profit_loss > self.pl:
            self.logger.info(f"Profit loss for trade {trade.id} is reached {profit_loss}. Sell all. Type: {trade.trade_direction}")
            return -trade.stake_amount
        elif profit_loss > (self.pl / 2 + self.pl / 4) and not closed_3_4:
            self.logger.info(f"Profit loss for trade {trade.id} is reached {profit_loss}. Sell 3/4 of stake. Type: {trade.trade_direction}")
            trade.set_custom_data(self.PL_SELL_3_4_KEY, True)
            return - (trade.stake_amount / 2)
        elif profit_loss > self.pl / 2 and not half_closed:
            self.logger.info(f"Profit loss for trade {trade.id} is reached {profit_loss}. Sell half of stake. Type: {trade.trade_direction}")
            trade.set_custom_data(self.PL_SELL_HALF_KEY, True)
            return - (trade.stake_amount / 2)
        else:
            return None
                    
                
      