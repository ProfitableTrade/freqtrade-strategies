# --- Do not remove these libs ---
import datetime
import logging
from typing import Optional, Tuple, Union
from freqtrade.strategy import IStrategy
from pandas import DataFrame
from freqtrade.persistence import Trade
from freqtrade.strategy import stoploss_from_open


class SettingsObject:
    bids_ask_delta: float
    depth: int
    volume_threshold: int
    
    def __init__(self, bids_ask_delta: float, depth: int, volume_threshold: int):
        self.bids_ask_delta = bids_ask_delta
        self.depth = depth
        self.volume_threshold = volume_threshold
        

# class GoogleSheetsImporter:
#     SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
#               "https://www.googleapis.com/auth/drive"]
#     client: Spreadsheet

#     def __init__(self):
#         json_data = json.loads(base64.b64decode("eyJ3ZWIiOnsiY2xpZW50X2lkIjoiNDM5OTg5NDc4OTE0LWc0Mm90cWNkbzQxdGRiaWEzczNnZzBiMXA0ZGpiN3FzLmFwcHMuZ29vZ2xldXNlcmNvbnRlbnQuY29tIiwicHJvamVjdF9pZCI6InByb21pc2luZy1mbGFzaC00MzUyMTItazMiLCJhdXRoX3VyaSI6Imh0dHBzOi8vYWNjb3VudHMuZ29vZ2xlLmNvbS9vL29hdXRoMi9hdXRoIiwidG9rZW5fdXJpIjoiaHR0cHM6Ly9vYXV0aDIuZ29vZ2xlYXBpcy5jb20vdG9rZW4iLCJhdXRoX3Byb3ZpZGVyX3g1MDlfY2VydF91cmwiOiJodHRwczovL3d3dy5nb29nbGVhcGlzLmNvbS9vYXV0aDIvdjEvY2VydHMiLCJjbGllbnRfc2VjcmV0IjoiR09DU1BYLUg5MnhTa3FWb1N6eHFudkY1Wjc5TjB4Y3lJdm8ifX0="))
#         credentials = ServiceAccountCredentials.from_json_keyfile_dict(json_data)
#         self.client = gspread.authorize(credentials).open_by_key("1C_NWy7a5EuDU6wz5xC5k2tPVfzKSV88WV4nhXYlqEsI")

#     def get_timeframe_settings(self, strategy, timeframe) -> SettingsObject:
        
#         sheet = self.client.worksheet(strategy)
#         self.timeframes_dics = {item['Timeframe']: SettingsObject(item["BidAskDelta"], item["Depth"], item["VolumeThreshold"]) for item in sheet.get_all_records()}

#         return self.timeframes_dics[timeframe]
# --------------------------------

class Strategy_Goal_Depth(IStrategy):
    """
    Strategy_Goal_Depth 
    author@: Yurii Udaltsov
    github@: https://github.com/freqtrade/freqtrade-strategies

    How to use it?
    > python3 ./freqtrade/main.py -s Strategy_Goal_Depth
    """

    INTERFACE_VERSION: int = 3
    BE_ACTIVATED: str = "be_activated"
    STAGE_1_SOLD: str = "stage_1_sold"
    STAGE_2_SOLD: str = "stage_2_sold"
    
    STRATEGY_SHEET_NAME = "DepthSpot"
    
    position_adjustment_enable = True

    # Оптимальний стоп-лосс або %max, розроблений для стратегії
    stoploss = -0.03
    
    use_custom_stoploss = True

    # Оптимальний таймфрейм для стратегії
    #timeframe = '15s'

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
    target_percent = 0.10
    
    target_stage_1 = 0.03
    target_stage_2 = 0.06
    
    stage_1_sell_amount = 0.3
    stage_2_sell_amount = 0.3

    
    def bot_start(self, **kwargs) -> None:
        self.logger = logging.getLogger(__name__)
        
        self.settings = SettingsObject(1.3, 10 , 1000)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Generates buy signal based on EMA indicators
        A buy signal is generated when EMA 15 crosses above EMA 30
        """
        
        order_book = self.dp.orderbook(metadata['pair'], self.settings.depth + 1)

        dataframe.loc[
            ((self.check_depth_of_market(order_book, self.settings.depth, self.settings.bids_ask_delta)) &
            (self.analyze_large_orders(order_book, self.settings.volume_threshold)) &
            (dataframe['volume'] > dataframe['volume'].shift(1)) &
            (dataframe['close'] < dataframe['close'].shift(1))),
            'enter_long'] = 1

        return dataframe


    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Generates sell signal based on EMA indicators
        A sell signal is generated when EMA 15 crosses below EMA 30
        """

        return dataframe
    
    def check_depth_of_market(self, order_book, depth, delta) -> bool:
        if len(order_book['bids']) < depth or len(order_book['asks']) < depth:
            return False
        
        total_bids = sum([bid[1] for bid in order_book['bids'][:depth]])
        total_asks = sum([ask[1] for ask in order_book['asks'][:depth]])
        
        self.logger.info(f"Analyzing depth of market... Results: total bids / total asks is {total_bids / total_asks}, configured delta is {delta}")
        
        return (total_bids / total_asks) > delta

    def analyze_large_orders(self, order_book, threshold) -> bool:
        large_orders = [order for order in order_book['bids'] if order[1] >= threshold] + \
                       [order for order in order_book['asks'] if order[1] >= threshold]

        self.logger.info(f"Analyzing large orders for threshold {threshold}, found {len(large_orders)}")
        
        return len(large_orders) > 0
    
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
            
            current_price_rate = current_rate / trade.open_rate - 1
            
            self.logger.info(f"Check for goal to be closed, price rate {current_price_rate}")
            
            if not stage_1_sold and current_price_rate >= self.target_stage_1:
                self.logger.info(f"Price rise up bigger than {self.target_percent * self.target_stage_1}, closing first target {self.stage_1_sell_amount}")
                trade.set_custom_data(self.STAGE_1_SOLD, True)
                return - ( trade.stake_amount * self.stage_1_sell_amount )
            elif not stage_2_sold and current_price_rate >= self.target_stage_2:
                self.logger.info(f"Price rise up bigger than {self.target_percent * self.target_stage_2}, closing second target {self.stage_2_sell_amount}")
                trade.set_custom_data(self.STAGE_2_SOLD, True)
                return - ( trade.stake_amount * self.stage_2_sell_amount )
            elif current_price_rate >= self.target_percent:
                return - trade.stake_amount
            else:
                return None
        except Exception as e:
            self.logger.info(f"Error occured during trade position adjustment: {str(e)}")
            return None