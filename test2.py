#
# from datetime import datetime
# import gspread
# from google.oauth2.service_account import Credentials
# from gspread import worksheet
#
#
# now = datetime.now()
#
# # ------------------------------
# # 구글 시트 기록 함수 (중복 체크 포함)
# # ------------------------------
#
# SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
# SERVICE_ACCOUNT_FILE = "quickstart.json"  # 서비스 계정 키 파일 경로
#
# creds = Credentials.from_service_account_file(
#     SERVICE_ACCOUNT_FILE, scopes=SCOPES
# )
# gc = gspread.authorize(creds)
#
# SPREADSHEET_KEY = "1BUIR05J52mNwRKRtGH3snb0bxa-NIynOhPW3lU6C0M4"  # 구글 시트 URL의 키
# spreadsheet = gc.open_by_key(SPREADSHEET_KEY)
# worksheet = spreadsheet.worksheet('API')
#
#
# def write_orders_to_sheet():
#     # 기존 ordererNo 목록 가져오기
#     existing_orders = set()
#     all_values = worksheet.get_all_values()
#     for row in all_values[1:]:  # 첫 행은 헤더\
#         print(row[0])
#         existing_orders.add(row[0])  # 첫 열이 ordererNo
#
#
#
# write_orders_to_sheet()
from collections import defaultdict

a  = ["S / Tami",
"XL / ZLuo",
"XL / 왕텐량",
"2XL / 관은우",
"M / 히하",
"M /Xuan Tung",
"M / ㅉ.ㄲ.ㅃ.",
"L/ Thanh Tung",
"S / 띤자",
"M / K.M",
"M / anhs",
"M / Davron",
"M / ABHISTHA",
"S / Ranjana",
"L / Natasha",
"2XL/ LEGION",
"L/ BIJAY@07",
"L / Shon",
"S / MANISHA",
"M / Ali",
"M / Hudaw",
"2XL/ Adham",
"XL / Mamur",
"M / Rusan",
"L / Muslimbek",
"2XL / CHO",
"L / Action Only",
"L / Global Art AI BOSS",
"3XL / B. J. Kim",
"L / SGP",
"L / E.J.Shin",
"XL / H.c h"]

print("")
print("")
value_dict = defaultdict(int)
for _ in a:
    b = _.split('/')
    # print(b[0].strip())
    value_dict[b[0].strip()] += 1
    # print(f"색상: 031 네이비 / 사이즈: {b[0].strip()}")

# for k, v in value_dict.items():
#     print(f"색상: 031 네이비 / 사이즈: {k}")
#
for k, v in value_dict.items():
    print(k, v)
















































윤영주	01037394479
박현영	01041679787
오선아	01028055704
권현정	01064732092

























































































































































































































































































































































































































































































































































































































































































































































