import gspread
import json
import base64

from oauth2client.service_account import ServiceAccountCredentials
from gspread.spreadsheet import Spreadsheet
from pydantic import BaseModel

class SettingsObject(BaseModel):
    bids_ask_delta: float
    depth: int
    volume_threshold: int


class GoogleSheetsImporter:
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
              "https://www.googleapis.com/auth/drive"]
    client: Spreadsheet

    def __init__(self):
        json_data = json.loads(base64.b64decode("eyJ3ZWIiOnsiY2xpZW50X2lkIjoiNDM5OTg5NDc4OTE0LWc0Mm90cWNkbzQxdGRiaWEzczNnZzBiMXA0ZGpiN3FzLmFwcHMuZ29vZ2xldXNlcmNvbnRlbnQuY29tIiwicHJvamVjdF9pZCI6InByb21pc2luZy1mbGFzaC00MzUyMTItazMiLCJhdXRoX3VyaSI6Imh0dHBzOi8vYWNjb3VudHMuZ29vZ2xlLmNvbS9vL29hdXRoMi9hdXRoIiwidG9rZW5fdXJpIjoiaHR0cHM6Ly9vYXV0aDIuZ29vZ2xlYXBpcy5jb20vdG9rZW4iLCJhdXRoX3Byb3ZpZGVyX3g1MDlfY2VydF91cmwiOiJodHRwczovL3d3dy5nb29nbGVhcGlzLmNvbS9vYXV0aDIvdjEvY2VydHMiLCJjbGllbnRfc2VjcmV0IjoiR09DU1BYLUg5MnhTa3FWb1N6eHFudkY1Wjc5TjB4Y3lJdm8ifX0="))
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(json_data)
        self.client = gspread.authorize(credentials).open_by_key("1C_NWy7a5EuDU6wz5xC5k2tPVfzKSV88WV4nhXYlqEsI")

    def get_timeframe_settings(self, strategy, timeframe) -> SettingsObject:
        
        sheet = self.client.worksheet(strategy)
        self.timeframes_dics = {item['Timeframe']: SettingsObject(item["BidAskDelta"], item["Depth"], item["VolumeThreshold"]) for item in sheet.get_all_records()}

        return self.timeframes_dics[timeframe]
