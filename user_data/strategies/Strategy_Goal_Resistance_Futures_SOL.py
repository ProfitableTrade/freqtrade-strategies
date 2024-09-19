# --- Do not remove these libs ---
import datetime
import logging
from typing import Optional, Tuple, Union
from freqtrade.strategy import IStrategy, informative
from pandas import DataFrame
from freqtrade.persistence import Trade
from freqtrade.strategy import stoploss_from_open
# --------------------------------

class Strategy_Goal_Resistance_Futures_SOL(IStrategy):
    """
    Strategy_Goal_Depth_Futures_SOL
    author@: Yurii Udaltsov and Illia
    github@: https://github.com/freqtrade/freqtrade-strategies

    How to use it?
    > python3 ./freqtrade/main.py -s Strategy_Goal_Depth
    """

    INTERFACE_VERSION: int = 3
    BE_ACTIVATED: str = "be_activated"
    STAGE_1_SOLD: str = "stage_1_sold"
    STAGE_2_SOLD: str = "stage_2_sold"
    
    position_adjustment_enable = True

    # Оптимальний стоп-лосс або %max, розроблений для стратегії
    stoploss = -0.02
    
    use_custom_stoploss = True
    
    can_short = True

    # Оптимальний таймфрейм для стратегії
    timeframe = '5m'

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
        'stoploss_on_exchange': True
    }
    
    # Settings for target reaching logic
    target_percent = 0.025
    
    target_stage_1 = 0.01
    target_stage_2 = 0.02
    
    stage_1_sell_amount = 0.33
    stage_2_sell_amount = 0.55
    
    
    def bot_start(self, **kwargs) -> None:
        self.logger = logging.getLogger(__name__)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Визначення рівнів підтримки та опору на основі останніх 25 свічок
        dataframe['support'], dataframe['resistance'] = self.calculate_support_resistance(dataframe, window=25)

        return dataframe
    
    def calculate_support_resistance(self, dataframe: DataFrame, window=25) -> Tuple[DataFrame, DataFrame]:
        # Розрахунок рівнів підтримки та опору на основі останніх 'window' свічок
        dataframe['support'] = dataframe['close'].rolling(window=window).min()
        dataframe['resistance'] = dataframe['close'].rolling(window=window).max()
        return dataframe['support'], dataframe['resistance']


    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        # Вхід в лонг на основі рівнів підтримки
        dataframe.loc[
            (dataframe['close'] < dataframe['support']) &      # Ціна нижче підтримки
            (dataframe['volume'] > dataframe['volume'].shift(1)),  # Обсяг зростає
            'enter_long'
            ] = 1

        # Вхід в шорт на основі рівнів опору
        dataframe.loc[
            (dataframe['close'] > dataframe['resistance']) &  # Ціна вище опору
            (dataframe['volume'] > dataframe['volume'].shift(1)),  # Обсяг зростає
            'enter_short'
            ] = 1
        
        self.logger.info(f"Support: {dataframe['support'].head(30)}, Resistance: {dataframe['resistance'].head(30)}")

        return dataframe

    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Вихід із лонгу на основі рівнів опору
        dataframe.loc[
            (dataframe['close'] >= dataframe['resistance']),  # Ціна досягає опору
            'exit_long'
            ] = 1

        # Вихід із шорту на основі рівнів підтримки
        dataframe.loc[
            (dataframe['close'] <= dataframe['support']),  # Ціна досягає підтримки
            'exit_short'
            ] = 1

        
        return dataframe
    
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: Optional[str], side: str,
                 **kwargs) -> float:
        
        return 4.0
    
    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float, after_fill: bool,
                        **kwargs) -> Optional[float]:
        try:
            be_activated = trade.get_custom_data(self.BE_ACTIVATED, default=False)
            
            current_price_rate = 0
            if trade.is_short:
                current_price_rate = trade.open_rate / current_rate - 1
            else:
                current_price_rate = current_rate / trade.open_rate - 1

            if be_activated or current_price_rate >= self.target_stage_1:
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
            
            current_price_rate = 0
            if trade.is_short:
                current_price_rate = trade.open_rate / current_rate - 1
            else:
                current_price_rate = current_rate / trade.open_rate - 1
            
            self.logger.info(f"Check for goal to be closed, price rate {current_price_rate}.")
            
            if not stage_1_sold and current_price_rate >= self.target_stage_1:
                self.logger.info(f"Price rise up bigger than {self.target_percent * self.target_stage_1}, closing first target {self.stage_1_sell_amount}.")
                trade.set_custom_data(self.STAGE_1_SOLD, True)
                return - ( trade.stake_amount * self.stage_1_sell_amount )
            elif not stage_2_sold and current_price_rate >= self.target_stage_2:
                self.logger.info(f"Price rise up bigger than {self.target_percent * self.target_stage_2}, closing second target {self.stage_2_sell_amount}.")
                trade.set_custom_data(self.STAGE_2_SOLD, True)
                return - ( trade.stake_amount * self.stage_2_sell_amount )
            elif current_price_rate >= self.target_percent:
                self.logger.info(f"Price rise up bigger than {self.target_percent}, closing order.")
                return - trade.stake_amount
            else:
                return None
        except Exception as e:
            self.logger.info(f"Error occured during trade position adjustment: {str(e)}")
            return None