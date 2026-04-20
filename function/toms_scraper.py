import asyncio
import re
from collections import defaultdict

from playwright.async_api import async_playwright

from static.static import TOMS_KOREA_ID, TOMS_KOREA_PW


# 사이즈 표기 정규화 (주문 데이터 → 사이트 표기)
SIZE_NORMALIZE = {
    '2XL': 'XXL',
    'XXL': 'XXL',
    'XL': 'XL',
    'L': 'L',
    'M': 'M',
    'S': 'S',
    '3XL': 'XXXL',
    'XXXL': 'XXXL',
    '4XL': '4XL',
    'FREE': 'FREE', 'F': 'FREE',
}


def extract_product_code(product_name):
    """상품명 마지막 상품코드 추출 (예: '083-BBT')"""
    match = re.search(r'(\d{2,5}-[A-Z]{2,4})(?:\s*$)', product_name.strip())
    return match.group(1) if match else None


def extract_color_code(color_str):
    """색상 문자열에서 3자리 코드 추출 (예: '003 모쿠그레이' → '003', '(시보리)031 네이비' → '031')"""
    match = re.search(r'(\d{3})', color_str.strip())
    return match.group(1) if match else None


async def login(page):
    await page.goto("https://www.toms-korea.com/login", wait_until="networkidle")
    await page.fill('input[name="code"]', TOMS_KOREA_ID)
    await page.fill('input[name="password"]', TOMS_KOREA_PW)
    await page.click('button[type="submit"]')
    await page.wait_for_load_state("networkidle")


async def fetch_add_to_cart():
    from function.fun_ss import get_daily_orders_from_sheet

    sheet_data = get_daily_orders_from_sheet()
    orders = sheet_data['orders']

    # 상품코드별로 (색상코드, 사이즈) → 수량 합산
    # {product_code: {(color_cd, size): qty}}
    product_map = defaultdict(lambda: defaultdict(int))

    for order in orders:
        for item in order['items']:
            if not item['size']:   # 사이즈 공란 제외
                continue
            code = extract_product_code(item['productName'])
            if not code:
                continue
            color_cd = extract_color_code(item['color'])
            if not color_cd:
                continue
            size = SIZE_NORMALIZE.get(item['size'], item['size'])
            try:
                qty = int(item['quantity'])
            except (ValueError, TypeError):
                continue
            product_map[code][(color_cd, size)] += qty

    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await login(page)

        for code, color_size_qty in product_map.items():
            # 상품 검색
            await page.goto(
                f"https://www.toms-korea.com/products/muji?keyword={code}",
                wait_until="networkidle"
            )
            product_links = await page.query_selector_all('a[href*="/products/detail"]')
            if not product_links:
                results.append({"code": code, "status": "상품 검색 실패", "items": []})
                continue

            detail_href = await product_links[0].get_attribute("href")
            if "?" not in detail_href:
                detail_href += "?kbn=muji"

            await page.goto(detail_href, wait_until="networkidle")
            await page.wait_for_timeout(500)

            # 사이즈 컬럼 인덱스 맵 추출
            sizes_info = await page.evaluate('''
                [...document.querySelectorAll("thead th")].slice(1).map((th, idx) => {
                    const label = th.querySelector("label.font-16px");
                    const raw = label ? label.innerText.trim() : "";
                    const parts = raw.split("\\n");
                    return { colIndex: idx + 1, sizeText: parts[parts.length - 1].trim() };
                })
            ''')
            size_to_col = {s['sizeText']: s['colIndex'] for s in sizes_info}
            # 사이즈 별칭 양방향 추가 (XXL↔2XL, XXXL↔3XL)
            for a, b in [('XXL', '2XL'), ('XXXL', '3XL')]:
                if a in size_to_col and b not in size_to_col:
                    size_to_col[b] = size_to_col[a]
                if b in size_to_col and a not in size_to_col:
                    size_to_col[a] = size_to_col[b]

            filled_items = []
            skipped_items = []

            for (color_cd, size), qty in color_size_qty.items():
                col_index = size_to_col.get(size)
                if col_index is None:
                    skipped_items.append({"color": color_cd, "size": size, "qty": qty, "reason": f"사이즈 없음 (가능: {list(size_to_col.keys())})"})
                    continue

                # 해당 색상코드 + 컬럼 인덱스의 input 찾기
                input_name = await page.evaluate(f'''
                    (function() {{
                        const inputs = [...document.querySelectorAll('input.quantity[data-color-cd="{color_cd}"]')];
                        const target = inputs.find(inp => {{
                            const cells = [...inp.closest("tr").children];
                            return cells.indexOf(inp.closest("td")) === {col_index};
                        }});
                        return target ? target.name : null;
                    }})()
                ''')

                if not input_name:
                    skipped_items.append({"color": color_cd, "size": size, "qty": qty, "reason": "색상/사이즈 조합 없음"})
                    continue

                await page.fill(f'input[name="{input_name}"]', str(qty))
                filled_items.append({"color": color_cd, "size": size, "qty": qty})

            if filled_items:
                await page.click('#btn-add-to-cart')
                await page.wait_for_load_state("networkidle")
                results.append({"code": code, "status": "장바구니 담기 완료", "items": filled_items, "skipped": skipped_items})
            else:
                results.append({"code": code, "status": "담을 항목 없음", "items": [], "skipped": skipped_items})

        await browser.close()

    return {"date": sheet_data['date'], "results": results}


def add_to_cart():
    return asyncio.run(fetch_add_to_cart())
