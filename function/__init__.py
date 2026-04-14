import json
import os

import gspread
from google.oauth2.service_account import Credentials

CLIENT_ID = "7Egc5QrSaVvqRsNAx8igL2"
CLIENT_SECRET = "$2a$04$L2Us1rT5.NcQurkuScTvtu"
BASE_URL = 'https://api.commerce.naver.com/external'

# 구글 API 인증
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_google_creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
if _google_creds_json:
    creds = Credentials.from_service_account_info(
        json.loads(_google_creds_json), scopes=SCOPES
    )
else:
    creds = Credentials.from_service_account_file("grd2-493312-9e7a5a4f6aa5.json", scopes=SCOPES)

gc = gspread.authorize(creds)

# 스프레드시트 열기
SPREADSHEET_KEY = "1BUIR05J52mNwRKRtGH3snb0bxa-NIynOhPW3lU6C0M4"  # 구글 시트 URL의 키
spreadsheet = gc.open_by_key(SPREADSHEET_KEY)
worksheet = spreadsheet.worksheet('API')

def orderer_template():
    return {
        'orderId': None,
        'ordererName': None,
        'ordererTel': None,
        'paymentMeans': None,
        'payLocationType': None,
        'productInfo': [],
        'name': None,
        'tel1': None,
        'zipCode': None,
        'baseAddress': None
    }

TOKEN_CACHE = {
    "token": None,
    "expire_at": 0  # timestamp
}