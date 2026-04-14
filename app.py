import requests
from flask import Flask, jsonify, request

from function.fun_ss import get_cached_token, order_detail_info_list, write_orders_to_sheet, get_daily_orders_from_sheet
from function.toms_scraper import add_to_cart

app = Flask(__name__)


@app.route('/')
def hello_world():  # put application's code here
    return '''
        기간: <input type="number" id="days" value="1" min="1" />일 </br></br>
        <button onclick="fetchOrders()">주문 리스트 가져오기</button>
        &nbsp;
        <button onclick="fetchDailyOrders(this)">당일 주문 리스트</button>
        &nbsp;
        <button onclick="runAddToCart(this)">톰스코리아 무지 장바구니 담기</button>
        <div id="cart-result" style="margin-top:16px;"></div>
        <div id="daily-result" style="margin-top:16px;"></div>
        <pre id="result"></pre>

        <script>
        function fetchOrders() {
            const days = document.getElementById('days').value;
            fetch('/orders?days=' + days)
              .then(res => res.json())
              .then(data => {
                document.getElementById('result').innerText = JSON.stringify(data, null, 2);
              });
        }

        function fetchDailyOrders(btn) {
            btn.disabled = true;
            btn.textContent = '불러오는 중...';
            const container = document.getElementById('daily-result');
            container.innerHTML = '<p>시트에서 당일 주문을 가져오는 중...</p>';
            fetch('/daily-orders')
              .then(res => res.json())
              .then(data => {
                btn.disabled = false;
                btn.textContent = '당일 주문 리스트';
                if (data.error) {
                    container.innerHTML = '<p style="color:red">오류: ' + data.error + '</p>';
                    return;
                }
                const orders = data.orders;
                let html = '<h3>당일 주문 (' + data.date + ' 이후, 총 ' + orders.length + '건)</h3>';
                html += '<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;font-size:13px;">';
                html += '<thead style="background:#f0f0f0;"><tr>';
                html += '<th>주문번호</th><th>주문자</th><th>수취인</th><th>주소</th><th>메모</th>';
                html += '<th>상품명</th><th>색상</th><th>사이즈</th><th>수량</th>';
                html += '</tr></thead><tbody>';
                orders.forEach(order => {
                    const items = order.items.filter(i => i.size);
                    if (!items.length) return;
                    items.forEach((item, idx) => {
                        html += '<tr>';
                        if (idx === 0) {
                            const rs = 'rowspan="' + items.length + '"';
                            html += '<td ' + rs + '>' + order.orderId + '</td>';
                            html += '<td ' + rs + '>' + order.ordererName + '<br><small>' + order.ordererTel + '</small></td>';
                            html += '<td ' + rs + '>' + order.recipientName + '<br><small>' + order.recipientTel + '</small></td>';
                            html += '<td ' + rs + '>' + order.address + '</td>';
                            html += '<td ' + rs + '>' + order.memo + '</td>';
                        }
                        html += '<td>' + item.productName + '</td>';
                        html += '<td>' + item.color + '</td>';
                        html += '<td>' + item.size + '</td>';
                        html += '<td style="text-align:center;">' + item.quantity + '</td>';
                        html += '</tr>';
                    });
                });
                html += '</tbody></table>';
                container.innerHTML = html;
              })
              .catch(err => {
                btn.disabled = false;
                btn.textContent = '당일 주문 리스트';
                container.innerHTML = '<p style="color:red">요청 실패: ' + err + '</p>';
              });
        }

        function runAddToCart(btn) {
            btn.disabled = true;
            btn.textContent = '처리 중...';
            const container = document.getElementById('cart-result');
            container.innerHTML = '<p>로그인 후 장바구니에 담는 중... (시간이 걸릴 수 있습니다)</p>';
            fetch('/toms/cart')
              .then(res => res.json())
              .then(data => {
                btn.disabled = false;
                btn.textContent = '톰스코리아 무지 장바구니 담기';
                if (data.error) {
                    container.innerHTML = '<p style="color:red">오류: ' + data.error + '</p>';
                    return;
                }
                let html = '<h3>장바구니 담기 결과 (' + data.date + ' 이후 주문)</h3>';
                html += '<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;font-size:13px;">';
                html += '<thead style="background:#f0f0f0;"><tr><th>상품코드</th><th>상태</th><th>담긴 항목</th><th>제외된 항목</th></tr></thead><tbody>';
                data.results.forEach(r => {
                    const ok = r.status === '장바구니 담기 완료';
                    const itemsStr = r.items.map(i => i.color + ' / ' + i.size + ' / ' + i.qty + '장').join('<br>');
                    const skipStr = (r.skipped || []).map(i => i.color + ' / ' + i.size + ' → ' + i.reason).join('<br>');
                    html += '<tr>';
                    html += '<td><b>' + r.code + '</b></td>';
                    html += '<td style="color:' + (ok ? 'green' : '#e63') + '">' + r.status + '</td>';
                    html += '<td>' + (itemsStr || '-') + '</td>';
                    html += '<td style="color:#999;font-size:11px;">' + (skipStr || '-') + '</td>';
                    html += '</tr>';
                });
                html += '</tbody></table>';
                container.innerHTML = html;
              })
              .catch(err => {
                btn.disabled = false;
                btn.textContent = '톰스코리아 무지 장바구니 담기';
                container.innerHTML = '<p style="color:red">요청 실패: ' + err + '</p>';
              });
        }
        </script>
        '''


@app.route('/orders')
def orders():
    days_value = int(request.args.get('days', 1))  # 기본값 1일
    token = get_cached_token()
    order_data = order_detail_info_list(token, days_value=days_value)
    write_orders_to_sheet(order_data)
    return jsonify(order_data)


@app.route('/daily-orders')
def daily_orders():
    try:
        data = get_daily_orders_from_sheet()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/toms/cart')
def toms_cart():
    try:
        result = add_to_cart()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run()
