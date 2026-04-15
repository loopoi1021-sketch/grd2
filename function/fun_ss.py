import random
import time
from collections import defaultdict
from datetime import datetime, timedelta

import bcrypt
import pybase64
import requests

from function import orderer_template, CLIENT_ID, CLIENT_SECRET, BASE_URL, worksheet, TOKEN_CACHE, spreadsheet
from static.static import DICT_PRODUCT_ID


def get_cached_token():
    now = int(time.time())
    if TOKEN_CACHE["token"] and now < TOKEN_CACHE["expire_at"]:
        return TOKEN_CACHE["token"]

    # 토큰 재발급
    res = get_token()
    TOKEN_CACHE["token"] = res["access_token"]
    TOKEN_CACHE["expire_at"] = now + int(res["expires_in"]) - 10  # 10초 안전 마진
    return TOKEN_CACHE["token"]


def get_token():
    timestamp = int(time.time() * 1000)
    # 밑줄로 연결하여 password 생성
    password = CLIENT_ID + "_" + str(timestamp)
    # bcrypt 해싱
    hashed = bcrypt.hashpw(password.encode('utf-8'), CLIENT_SECRET.encode('utf-8'))
    # base64 인코딩
    client_secret_sign = pybase64.standard_b64encode(hashed).decode('utf-8')

    url = f"{BASE_URL}/v1/oauth2/token"

    payload = {
        'client_id': CLIENT_ID,
        'timestamp': timestamp,
        'grant_type': 'client_credentials',
        'client_secret_sign': client_secret_sign,
        'type': 'SELF'
    }
    headers = {
      'Content-Type': 'application/x-www-form-urlencoded',
      'Accept': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    res_data = response.json()
    return res_data


def order_detail_info_list(token, days_value=1):
    headers = {'Authorization': token}
    url = f"{BASE_URL}/v1/pay-order/seller/product-orders"

    now = datetime.now()
    data_info = defaultdict(orderer_template)

    for _ in range(0, days_value):
        from_time = (now - timedelta(days=_)).strftime("%Y-%m-%dT%H:%M:%S.000+09:00")

        params = {
            'from': from_time,
            'rangeType': 'PAYED_DATETIME',
            'placeOrderStatusType': 'OK',
        }

        # 재시도 로직
        retry_count = 0
        while True:
            try:
                res = requests.get(url=url, headers=headers, params=params)

                if res.status_code == 429:  # Too Many Requests
                    retry_count += 1
                    wait_time = min(2 ** retry_count, 30)  # 백오프 (최대 30초)
                    print(f"[WARN] 429 Too Many Requests. {wait_time}초 대기 후 재시도... (시도 {retry_count})")
                    time.sleep(wait_time)
                    continue  # 다시 시도

                res.raise_for_status()  # 다른 HTTP 에러 발생 시 예외
                res_data = res.json()
                break  # 요청 성공하면 while 루프 탈출

            except requests.exceptions.RequestException as e:
                retry_count += 1
                wait_time = min(2 ** retry_count, 30)
                print(f"[ERROR] 요청 실패: {e}. {wait_time}초 대기 후 재시도... (시도 {retry_count})")
                time.sleep(wait_time)
                if retry_count >= 5:  # 최대 5회 재시도
                    print("[ERROR] 요청 재시도 횟수 초과.")
                    return data_info

        # 0.1초 대기 (API 요청 간 텀)
        time.sleep(0.1)

        if res_data['data'].get('contents'):

            for data in res_data['data']['contents']:
                content_info = data['content']
                order_info = content_info['order']
                productOrder_info = content_info['productOrder']
                shippingAddress = productOrder_info['shippingAddress']

                orderId = order_info['orderId']
                data_info[orderId].update({
                    'orderId': orderId,
                    'ordererName': order_info['ordererName'],
                    'ordererTel': order_info['ordererTel'],
                    'paymentMeans': order_info['paymentMeans'],
                    'payLocationType': order_info['payLocationType'],
                    'name': shippingAddress['name'],
                    'tel1': shippingAddress['tel1'],
                    'zipCode': shippingAddress['zipCode'],
                    'baseAddress': f"{shippingAddress['baseAddress']} {shippingAddress.get('detailedAddress', '')}"
                })
                data_info[orderId]['productInfo'].append({
                    'productName': productOrder_info['productName'],
                    'productOption': productOrder_info['productOption'],
                    'quantity': productOrder_info['quantity'],
                    'productId': productOrder_info['productId'],
                })

    return data_info


# ------------------------------
# 구글 시트 기록 함수 (중복 체크 포함)
# ------------------------------
def write_orders_to_sheet(order_data):
    # 기존 ordererNo 목록 가져오기
    existing_orders = set()
    all_values = worksheet.get_all_values()
    for row in all_values[1:]:  # 첫 행은 헤더
        existing_orders.add(row[0])  # 첫 열이 ordererNo

    current_row_count = len(all_values)  # 현재 시트 데이터 행 수
    start_row = current_row_count + 1  # 새로 데이터가 추가될 첫 행 번호
    groups_to_add = []

    # 데이터 추가
    for order_idx, order in enumerate(order_data.values()):
        if order['orderId'] in existing_orders:
            continue  # 이미 있으면 스킵

        product_info_list = order['productInfo']
        order_start_row = start_row  # 해당 주문의 시작 행

        for idx, product in enumerate(product_info_list):
            row_data = []
            productId = product.get('productId')
            productName = DICT_PRODUCT_ID.get(productId, product.get('productName'))
            if len(product.get('productName')) < 7:
                productName = product.get('productName')

            if productId == '12305233385':
                suffix = ' 110-CLL' if '(시보리)' in product.get('productOption', '') else ' 102-CVL'
                productName += suffix
            elif productId == '12016880708':
                suffix = ' 271-BFC' if '(오버핏기모)' in product.get('productOption', '') else ' 219-MLC'
                productName += suffix

            seonghyang = ""
            productOption = product.get("productOption", "")
            if productId == '13227888471':
                parts = productOption.split("/")
                converted_parts = []
                for part in parts:
                    part = part.strip()
                    if part.startswith("성향:"):
                        seonghyang = part[3:].strip()
                        converted_parts.append("색상: 005 블랙")
                    else:
                        converted_parts.append(part)
                productOption = " / ".join(converted_parts)

            if idx == 0:
                worksheet.append_row([
                    order.get("orderId"),
                    order.get("ordererName"),
                    order.get("ordererTel"),
                    productName,
                    productOption,
                    product.get("quantity"),
                    order.get("name"),
                    order.get("tel1"),
                    order.get("zipCode"),
                    order.get("baseAddress"),
                    seonghyang,
                ])
            else:
                worksheet.append_row([
                    " ", " ", " ",
                    productName,
                    productOption,
                    product.get("quantity"),
                    " ", " ", " ", " ",
                    seonghyang,
                ])
            start_row += 1

        order_end_row = start_row - 1
        if order_end_row > order_start_row:
            groups_to_add.append((order_start_row, order_end_row))

        print(f"[WRITE] 주문 {order['orderId']} 기록 완료. (행 {order_start_row}~{order_end_row})")

    # 그룹화 적용
    if groups_to_add:
        groups_requests = []
        for start, end in groups_to_add:
            print(start, end)
            groups_requests.append({
                "addDimensionGroup": {
                    "range": {
                        "sheetId": worksheet.id,
                        "dimension": "ROWS",
                        "startIndex": start,  # 0-based
                        "endIndex": end          # end는 미포함
                    }
                }
            })
        worksheet.spreadsheet.batch_update({"requests": groups_requests})


def get_daily_orders_from_sheet():
    """마지막 결합(merge)된 날짜 구분 행 이후의 당일 주문 데이터를 반환."""
    sheet_metadata = spreadsheet.fetch_sheet_metadata()
    all_values = worksheet.get_all_values()

    # API 시트에서 전체 행 merge 찾기 (startColumnIndex=0, endColumnIndex=12)
    last_merge_row = 0
    last_merge_date = ""
    for s in sheet_metadata.get('sheets', []):
        if s.get('properties', {}).get('title') == 'API':
            for m in s.get('merges', []):
                if m['startColumnIndex'] == 0 and m['endColumnIndex'] == 12:
                    if m['startRowIndex'] > last_merge_row:
                        last_merge_row = m['startRowIndex']
                        last_merge_date = all_values[last_merge_row][0] if last_merge_row < len(all_values) else ""
            break

    # 결합 행 다음 행부터 끝까지
    rows = all_values[last_merge_row + 1:]

    orders = []
    current_order = None

    for row in rows:
        order_id = row[0]
        is_continuation = order_id.strip() in ('', ' ')

        if not is_continuation:
            # 새 주문 시작
            current_order = {
                "orderId": order_id,
                "ordererName": row[1],
                "ordererTel": row[2],
                "recipientName": row[6],
                "recipientTel": row[7],
                "zipCode": row[8],
                "address": row[9],
                "memo": row[10] if len(row) > 10 else "",
                "items": [],
            }
            orders.append(current_order)

        if current_order is not None:
            product_name = row[3]
            option = row[4]   # "색상: XXX / 사이즈: YYY"
            quantity = row[5]

            color, size = "", ""
            if ("색상:" in option or "성향:" in option) and "사이즈:" in option:
                parts = option.split("/")
                for part in parts:
                    part = part.strip()
                    if part.startswith("색상:"):
                        color = part[3:].strip()
                    elif part.startswith("성향:"):
                        color = "005 블랙"
                    elif part.startswith("사이즈:"):
                        size = part[4:].strip()
            else:
                color = option

            current_order["items"].append({
                "productName": product_name,
                "color": color,
                "size": size,
                "quantity": quantity,
            })

    return {"date": last_merge_date, "orders": orders}