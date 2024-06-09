# --- Do not remove these libs ---
import datetime
import logging
from typing import Optional, Tuple, Union
from freqtrade.strategy import IStrategy
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
from pandas import DataFrame
from freqtrade.persistence import Trade
from freqtrade.strategy import stoploss_from_open
# --------------------------------

class Strategy_Goal_KAVAUSDT(IStrategy):
    """
    Strategy_Goal_KAVAUSDT
    author@: Yurii Udaltsov
    github@: https://github.com/freqtrade/freqtrade-strategies

    How to use it?
    > python3 ./freqtrade/main.py -s Strategy_Goal_KAVAUSDT
    """

    INTERFACE_VERSION: int = 3
    BE_ACTIVATED: str = "be_activated"
    STAGE_1_SOLD: str = "stage_1_sold"
    STAGE_2_SOLD: str = "stage_2_sold"
    STAGE_3_SOLD: str = "stage_3_sold"
    
    position_adjustment_enable = True

    # Оптимальний стоп-лосс або %max, розроблений для стратегії
    stoploss = -0.03
    
    use_custom_stoploss = True

    # Оптимальний таймфрейм для стратегії
    timeframe = '30m'

    # Налаштування трейлінг стоп-лосу
    # trailing_stop = True  # Включення трейлінг стоп-лосу
    # trailing_stop_positive = 0.033  # Трейлінг стоп активується, коли прибуток досягає 3,3%
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
    
    # Settings for target reaching logic
    target_percent = 0.109
    
    target_stage_1 = 0.1
    target_stage_2 = 0.3
    target_stage_3 = 0.65
    
    stage_1_sell_amount = 0.3
    stage_2_sell_amount = 0.3
    stage_3_sell_amount = 0.25
    
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
    
    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float, after_fill: bool,
                        **kwargs) -> Optional[float]:
        try:
            be_activated = trade.get_custom_data(self.BE_ACTIVATED, default=False)
            
            current_price_rate = current_rate / trade.open_rate - 1

            if be_activated or current_price_rate >= self.target_percent * self.target_stage_1:
                if not be_activated: 
                    trade.set_custom_data(self.BE_ACTIVATED, True)
                    
                return stoploss_from_open(0.002, current_profit, is_short=trade.is_short, leverage=trade.leverage)

            return None
        except Exception as e:
            self.logger.info(f"Error occured during custom stoploss definition: {str(e)}")
            return None
    
    def adjust_trade_position(self, trade: Trade, current_time: datetime,
                              current_rate: float, current_profit: float,
                              min_stake: Optional[float], max_stake: float,
                              current_entry_rate: float, current_exit_rate: float,
                              current_entry_profit: float, current_exit_profit: float,
                              **kwargs
                              ) -> Union[Optional[float], Tuple[Optional[float], Optional[str]]]:
        try:
            stage_1_sold = trade.get_custom_data(self.STAGE_1_SOLD, default=False)
            stage_2_sold = trade.get_custom_data(self.STAGE_2_SOLD, default=False)
            stage_3_sold = trade.get_custom_data(self.STAGE_3_SOLD, default=False)
            
            current_price_rate = current_rate / trade.open_rate - 1
            
            
            self.logger.info(f"Check for goal to be closed, price rate {current_price_rate}")
            
            if not stage_1_sold and current_price_rate >= self.target_percent * self.target_stage_1:
                self.logger.info(f"Price rise up bigger than {self.target_percent * self.target_stage_1}, closing first target {self.stage_1_sell_amount}")
                trade.set_custom_data(self.STAGE_1_SOLD, True)
                return - ( trade.stake_amount * self.stage_1_sell_amount )
            elif not stage_2_sold and current_price_rate >= self.target_percent * self.target_stage_2:
                self.logger.info(f"Price rise up bigger than {self.target_percent * self.target_stage_2}, closing second target {self.stage_2_sell_amount}")
                trade.set_custom_data(self.STAGE_2_SOLD, True)
                return - ( trade.stake_amount * self.stage_2_sell_amount )
            elif not stage_3_sold and current_price_rate >= self.target_percent * self.target_stage_3:
                self.logger.info(f"Price rise up bigger than {self.target_percent * self.target_stage_3}, closing third target {self.stage_3_sell_amount}")
                trade.set_custom_data(self.STAGE_3_SOLD, True)
                return - ( trade.stake_amount * self.stage_3_sell_amount )
            elif current_price_rate >= self.target_percent:
                return - trade.stake_amount
            else:
                return None
        except Exception as e:
            self.logger.info(f"Error occured during trade position adjustment: {str(e)}")
            return None