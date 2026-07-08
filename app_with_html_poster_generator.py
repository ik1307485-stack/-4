import streamlit as st
import requests
import io
import base64
import html
import os
import tempfile
from playwright.sync_api import sync_playwright


GOLD_PRICE = 4600
WORK_VYSHYVANKA = 3100
WORK_INDIVIDUAL = 3000
WORK_RING = 6100
PACKAGING = 3000
K = 13

STONE_PRICES_USD = {
    "Натуральні діаманти": {
        "1 мм": 9,
        "1.25 мм": 15,
        "1.5 мм": 24,
        "1.75 мм": 42,
        "2 мм": 55,
        "2.5 мм": 100,
        "3 мм": 220,
        "3.5 мм": 380,
        "4 мм": 800,
    },
    "Лабораторні діаманти": {
        "1 мм": 7,
        "1.25 мм": 10,
        "1.5 мм": 15,
        "1.75 мм": 30,
        "2 мм": 30,
        "2.5 мм": 60,
        "3 мм": 140,
        "3.5 мм": 210,
        "4 мм": 390,
    },
    "Муасаніти": {
        "1 мм": 5,
        "1.25 мм": 7,
        "1.5 мм": 9,
        "1.75 мм": 14,
        "2 мм": 16,
        "2.5 мм": 30,
        "3 мм": 60,
        "3.5 мм": 104,
        "4 мм": 154,
    },
}


def get_usd_rate():
    try:
        url = "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?json"
        data = requests.get(url, timeout=5).json()

        for item in data:
            if item.get("cc") == "USD":
                return float(item.get("rate"))
    except Exception:
        pass

    return 44.5


def money(value):
    return f"{value:,.0f}".replace(",", " ")


def money100(value):
    value = round(value / 100) * 100
    return f"{value:,.0f}".replace(",", " ")


def calc_weight(size, width, thickness):
    w = width / 10
    t = thickness / 10
    length = ((size * 3.14) / 10) + (thickness / 10) * 3
    return length * w * t * K


def get_work_price(product_type, design=None):
    if product_type == "Каблучка":
        return WORK_RING

    if design == "Вишиванка":
        return WORK_VYSHYVANKA

    return WORK_INDIVIDUAL


def get_stone_cost_by_type(stone_type, stone_size, qty, usd_rate):
    if qty <= 0:
        return 0, 0

    price_usd = STONE_PRICES_USD[stone_type][stone_size]
    total_usd = price_usd * qty
    total_uah = total_usd * usd_rate

    return total_usd, total_uah


def make_inserts_text(main_size, main_qty, small_size, small_qty):
    parts = []

    if main_qty > 0:
        parts.append(f"{main_size} - {main_qty} шт")

    if small_qty > 0:
        parts.append(f"{small_size} - {small_qty} шт")

    return "; ".join(parts) if parts else "не додано"




def get_font(size, bold=False):
    """Підбирає шрифт, який нормально підтримує українську мову."""
    font_paths = []

    # 1) Часто є на Streamlit Cloud / Linux
    if bold:
        font_paths += [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf",
            "/usr/share/fonts/truetype/noto/NotoSerif-Bold.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
        ]
    else:
        font_paths += [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf",
            "/usr/share/fonts/truetype/noto/NotoSerif-Regular.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        ]

    # 2) Якщо є matplotlib — він майже завжди має DejaVu Sans всередині
    try:
        import matplotlib.font_manager as fm
        font_paths.append(fm.findfont("DejaVu Sans", fallback_to_default=True))
    except Exception:
        pass

    # 3) Локальні назви
    font_paths += [
        "DejaVuSans.ttf",
        "DejaVuSerif.ttf",
        "Arial.ttf",
    ]

    for font_path in font_paths:
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            continue

    return ImageFont.load_default()


def text_width(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def draw_center(draw, text, y, font, fill, canvas_width):
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (canvas_width - (bbox[2] - bbox[0])) / 2
    draw.text((x, y), text, font=font, fill=fill)


def wrap_text(draw, text, font, max_width):
    words = str(text).split()
    lines = []
    current = ""

    for word in words:
        test = word if not current else current + " " + word
        if text_width(draw, test, font) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines


def remove_light_background(img):
    """Робить білий/світлий фон прозорим, щоб фото лягало на чорний фон."""
    img = img.convert("RGBA")
    pixels = img.load()
    w, h = img.size

    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]

            # Білий або майже білий фон
            if r > 225 and g > 225 and b > 225:
                pixels[x, y] = (r, g, b, 0)
            # Дуже світло-сірий фон
            elif r > 210 and g > 210 and b > 210 and abs(r - g) < 18 and abs(g - b) < 18:
                pixels[x, y] = (r, g, b, 0)

    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)

    return img



def fit_font(draw, text, start_size, max_width, bold=False, min_size=24):
    """Підбирає найбільший шрифт, щоб текст вліз у ширину."""
    size = start_size
    while size >= min_size:
        font = get_font(size, bold=bold)
        lines = wrap_text(draw, text, font, max_width)
        if all(text_width(draw, line, font) <= max_width for line in lines):
            return font, lines
        size -= 2
    font = get_font(min_size, bold=bold)
    return font, wrap_text(draw, text, font, max_width)


def draw_text_center(draw, text, y, font, fill, canvas_width, stroke=0):
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke)
    x = (canvas_width - (bbox[2] - bbox[0])) / 2
    draw.text(
        (x, y),
        text,
        font=font,
        fill=fill,
        stroke_width=stroke,
        stroke_fill="#000000",
    )


def draw_text_box_center(draw, text, center_x, y, font, fill, max_width, max_lines=2, line_gap=8):
    lines = wrap_text(draw, text, font, max_width)
    yy = y
    for line in lines[:max_lines]:
        bbox = draw.textbbox((0, 0), line, font=font, stroke_width=1)
        x = center_x - (bbox[2] - bbox[0]) / 2
        draw.text(
            (x, yy),
            line,
            font=font,
            fill=fill,
            stroke_width=1,
            stroke_fill="#000000",
        )
        yy += (bbox[3] - bbox[1]) + line_gap


def generate_client_image(uploaded_image, poster_data):
    W, H = 1080, 1350

    uploaded_image.seek(0)
    image_bytes = uploaded_image.read()
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    title = poster_data.get("title", "Індивідуальна модель обручок").replace("⚜️", "").strip()
    gold = poster_data.get("gold", "Біле родоване золото 585 проби").replace("💍", "").strip()
    sizes = poster_data.get("sizes", "").replace("Розміри: ", "").replace("Розмір: ", "").strip()
    widths = poster_data.get("widths", "").replace("Ширина: ", "").strip()
    coating = poster_data.get("coating", "").replace("Покриття: ", "").strip()
    weight = poster_data.get("weight", "").replace("Середня вага виробу: ", "").strip()
    price = poster_data.get("price", "")
    inserts = poster_data.get("inserts", "").replace("Вставки: ", "").strip()

    size_label = "РОЗМІРИ" if "та" in sizes else "РОЗМІР"

    columns = [
        ("ЗОЛОТО", "Біле родоване<br>585 проби"),
        (size_label, sizes),
        ("ШИРИНА", widths),
        ("ПОКРИТТЯ", coating),
        ("ВАГА", weight),
    ]

    if inserts and inserts != "не додано":
        columns.append(("ВСТАВКИ", inserts))

    columns_html = ""
    for label, value in columns:
        columns_html += f'''
        <div class="spec-col">
            <div class="spec-label">{html.escape(label)}</div>
            <div class="spec-value">{value}</div>
        </div>
        '''

    safe_title = html.escape(title.upper()).replace("«", "&laquo;").replace("»", "&raquo;")
    safe_gold = html.escape(gold.upper())

    html_doc = f'''
<!DOCTYPE html>
<html lang="uk">
<head>
<meta charset="utf-8" />
<style>
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; background: #000; width: {W}px; height: {H}px; }}
    body {{
        font-family: Georgia, "Times New Roman", "DejaVu Serif", serif;
        color: #f5f0ea;
        overflow: hidden;
    }}
    .poster {{
        width: {W}px;
        height: {H}px;
        background:
            radial-gradient(circle at 50% 37%, rgba(220,160,90,0.14), transparent 34%),
            linear-gradient(180deg, #030303 0%, #000 55%, #030303 100%);
        position: relative;
        overflow: hidden;
    }}
    .title {{
        position: absolute;
        top: 48px;
        left: 70px;
        right: 70px;
        text-align: center;
        color: #e69a60;
        font-size: 62px;
        line-height: 1.16;
        letter-spacing: 3px;
        text-transform: uppercase;
        text-shadow: 0 2px 12px rgba(230,154,96,0.28);
        font-weight: 500;
    }}
    .subtitle {{
        position: absolute;
        top: 210px;
        left: 70px;
        right: 70px;
        text-align: center;
        color: #f2f2f2;
        font-size: 32px;
        line-height: 1.2;
        letter-spacing: 2px;
        text-transform: uppercase;
        text-shadow: 0 2px 10px rgba(255,255,255,0.25);
    }}
    .image-wrap {{
        position: absolute;
        left: 110px;
        top: 285px;
        width: 860px;
        height: 560px;
        display: flex;
        align-items: center;
        justify-content: center;
    }}
    #productCanvas {{
        max-width: 860px;
        max-height: 560px;
        object-fit: contain;
        filter: drop-shadow(0 30px 40px rgba(0,0,0,0.9));
    }}
    .specs {{
        position: absolute;
        top: 890px;
        left: 56px;
        right: 56px;
        height: 145px;
        display: grid;
        grid-template-columns: repeat({len(columns)}, 1fr);
        border-bottom: 2px solid #c9824d;
        padding-bottom: 28px;
    }}
    .spec-col {{
        text-align: center;
        padding: 0 16px;
        border-right: 2px solid #c9824d;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: flex-start;
    }}
    .spec-col:last-child {{ border-right: none; }}
    .spec-label {{
        color: #e69a60;
        font-size: {24 if len(columns) == 6 else 28}px;
        letter-spacing: 1.4px;
        margin-bottom: 22px;
        white-space: nowrap;
        font-weight: 600;
    }}
    .spec-value {{
        color: #f7f7f7;
        font-size: {29 if len(columns) == 6 else 34}px;
        line-height: 1.25;
        text-shadow: 0 2px 8px rgba(255,255,255,0.18);
        word-break: normal;
    }}
    .price-label {{
        position: absolute;
        top: 1095px;
        left: 80px;
        right: 80px;
        color: #e69a60;
        text-align: center;
        font-size: 34px;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        font-weight: 700;
    }}
    .price {{
        position: absolute;
        top: 1160px;
        left: 80px;
        right: 80px;
        color: #e69a60;
        text-align: center;
        font-size: 76px;
        line-height: 1;
        letter-spacing: 2px;
        text-shadow: 0 2px 14px rgba(230,154,96,0.35);
    }}
    .brand {{
        position: absolute;
        bottom: 32px;
        left: 0;
        right: 0;
        text-align: center;
        color: #9b9b9b;
        font-family: Arial, "DejaVu Sans", sans-serif;
        font-size: 30px;
        letter-spacing: 5px;
        font-weight: 300;
    }}
</style>
</head>
<body>
<div class="poster">
    <div class="title">{safe_title}</div>
    <div class="subtitle">{safe_gold}</div>

    <div class="image-wrap">
        <canvas id="productCanvas"></canvas>
    </div>

    <div class="specs">
        {columns_html}
    </div>

    <div class="price-label">СЕРЕДНЯ ВАРТІСТЬ ВИРОБУ:</div>
    <div class="price">{html.escape(price)} грн 💎</div>
    <div class="brand">LANA &amp; LONA</div>
</div>

<script>
const src = "data:image/png;base64,{image_b64}";
const img = new Image();
img.onload = () => {{
    const maxW = 860;
    const maxH = 560;
    let w = img.width;
    let h = img.height;
    const scale = Math.min(maxW / w, maxH / h, 1);
    w = Math.round(w * scale);
    h = Math.round(h * scale);

    const canvas = document.getElementById("productCanvas");
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(img, 0, 0, w, h);

    const imageData = ctx.getImageData(0, 0, w, h);
    const d = imageData.data;
    for (let i = 0; i < d.length; i += 4) {{
        const r = d[i], g = d[i + 1], b = d[i + 2];
        if (r > 238 && g > 238 && b > 238) {{
            d[i + 3] = 0;
        }} else if (r > 218 && g > 218 && b > 218) {{
            const alpha = Math.max(0, 255 - (Math.min(r,g,b) - 218) * 9);
            d[i + 3] = Math.min(d[i + 3], alpha);
        }}
    }}
    ctx.putImageData(imageData, 0, 0);
}};
img.src = src;
</script>
</body>
</html>
'''

    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html_doc)
        html_path = f.name

    try:
        with sync_playwright() as p:
            chromium_path = "/usr/bin/chromium"
            launch_kwargs = {"headless": True, "args": ["--no-sandbox", "--disable-dev-shm-usage"]}
            if os.path.exists(chromium_path):
                launch_kwargs["executable_path"] = chromium_path

            browser = p.chromium.launch(**launch_kwargs)
            page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
            page.goto("file://" + html_path, wait_until="networkidle")
            page.wait_for_timeout(700)
            png_bytes = page.locator(".poster").screenshot(type="png")
            browser.close()
    finally:
        try:
            os.remove(html_path)
        except Exception:
            pass

    return io.BytesIO(png_bytes)


def calculate_wedding_rings(data):
    usd_rate = get_usd_rate()

    size_1 = data["size_1"]
    width_1 = data["width_1"]
    thickness_1 = data["thickness_1"]

    use_second_ring = data.get("use_second_ring", True)

    size_2 = data["size_2"] if use_second_ring else 0
    width_2 = data["width_2"] if use_second_ring else 0
    thickness_2 = data["thickness_2"] if use_second_ring else 0

    design = data["design"]
    coating_usd = data["coating_usd"]
    coating_uah = coating_usd * usd_rate
    engraving = data["engraving"]
    delivery = data["delivery"]
    discount_percent = data["discount_percent"]

    ring_stone_enabled = data["ring_stone_enabled"]
    ring_stone_size = data["ring_stone_size"]
    ring_stone_qty = data["ring_stone_qty"] if ring_stone_enabled else 0

    manual_weight_1 = data.get("manual_weight_1", 0)
    manual_weight_2 = data.get("manual_weight_2", 0)

    auto_weight_1 = calc_weight(size_1, width_1, thickness_1)
    auto_weight_2 = calc_weight(size_2, width_2, thickness_2) if use_second_ring else 0

    if manual_weight_1 > 0:
        weight_1 = manual_weight_1
        weight_note_1 = "Вага виробу 1 задана вручну"
    else:
        weight_1 = auto_weight_1
        weight_note_1 = "Вага виробу 1 розрахована автоматично"

    if use_second_ring:
        if manual_weight_2 > 0:
            weight_2 = manual_weight_2
            weight_note_2 = "Вага виробу 2 задана вручну"
        else:
            weight_2 = auto_weight_2
            weight_note_2 = "Вага виробу 2 розрахована автоматично"
    else:
        weight_2 = 0
        weight_note_2 = "Друга обручка не додана"

    total_weight = weight_1 + weight_2

    work_per_gram = get_work_price("Пара обручок", design)
    work_cost = total_weight * work_per_gram
    discount = work_cost * (discount_percent / 100)
    work_after_discount = work_cost - discount
    gold_cost = total_weight * GOLD_PRICE

    base_total_without_stones = (
        gold_cost
        + work_after_discount
        + PACKAGING
        + engraving
        + coating_uah
        + delivery
    )

    stones_usd, stones_uah = get_stone_cost_by_type(
        "Натуральні діаманти",
        ring_stone_size,
        ring_stone_qty,
        usd_rate,
    )

    total = base_total_without_stones + stones_uah

    title = (
        "Індивідуальна модель обручок «Вишиванка» ⚜️"
        if design == "Вишиванка"
        else "Індивідуальна модель обручок ⚜️"
    )

    coating_client = "Без покриття" if coating_usd == 0 else "Родій"

    inserts_text = "не додано"
    if ring_stone_qty > 0:
        inserts_text = f"{ring_stone_size} - {ring_stone_qty} шт"

    second_weight_text = ""
    if use_second_ring:
        second_weight_text = f"""
{weight_note_2}:
{weight_2:.2f} г
"""

    if use_second_ring:
        client_sizes_text = f"Розміри: {size_1:g} та {size_2:g}"
        client_width_text = f"Ширина: {width_1:g} мм та {width_2:g} мм"
    else:
        client_sizes_text = f"Розмір: {size_1:g}"
        client_width_text = f"Ширина: {width_1:g} мм"

    technical_text = f"""Курс USD: {usd_rate:.2f} грн

Тип виробу:
Пара обручок

{weight_note_1}:
{weight_1:.2f} г
{second_weight_text}
Загальна вага:
{total_weight:.2f} г

Золото:
{money(gold_cost)} грн

Робота:
{money(work_cost)} грн

Знижка:
-{money(discount)} грн

Робота після знижки:
{money(work_after_discount)} грн

Упаковка:
{money(PACKAGING)} грн

Гравіювання:
{money(engraving)} грн

Покриття:
{money(coating_uah)} грн

Діаманти / каміння:
{money(stones_uah)} грн ({stones_usd}$)

Доставка:
{money(delivery)} грн

=====================
ДО СПЛАТИ:
{money(total)} грн
"""

    client_text = f"""{title}

Біле родоване золото 585 проби 💍
{client_sizes_text}
{client_width_text}
Покриття: {coating_client}
Середня вага виробу: {total_weight:.1f} г
"""

    if ring_stone_qty > 0:
        variant_totals = {}

        for stone_type in STONE_PRICES_USD.keys():
            _, stone_uah_variant = get_stone_cost_by_type(
                stone_type,
                ring_stone_size,
                ring_stone_qty,
                usd_rate,
            )
            variant_totals[stone_type] = base_total_without_stones + stone_uah_variant

        client_text += f"""Вставки: {inserts_text}

Середня вартість виробу:
• з натуральними діамантами:
{money100(variant_totals["Натуральні діаманти"])} грн 💎
• з лабораторними діамантами:
{money100(variant_totals["Лабораторні діаманти"])} грн 💎
• з муасанітами:
{money100(variant_totals["Муасаніти"])} грн 💎
"""
    else:
        client_text += f"""
Середня вартість виробу:
{money100(total)} грн 💎
"""

    poster_data = {
        "title": title,
        "gold": "Біле родоване золото 585 проби 💍",
        "sizes": client_sizes_text,
        "widths": client_width_text,
        "coating": f"Покриття: {coating_client}",
        "weight": f"Середня вага виробу: {total_weight:.1f} г",
        "price": money100(total),
    }

    return technical_text, client_text, poster_data


def calculate_ring(data):
    usd_rate = get_usd_rate()

    size = data["size"]
    width = data["width"]
    thickness = data["thickness"]
    coating_usd = data["coating_usd"]
    coating_uah = coating_usd * usd_rate
    engraving = data["engraving"]
    delivery = data["delivery"]
    discount_percent = data["discount_percent"]
    main_size = data["main_size"]
    main_qty = data["main_qty"]
    small_size = data["small_size"]
    small_qty = data["small_qty"]
    manual_weight = data.get("manual_weight", 0)

    auto_weight = calc_weight(size, width, thickness)

    if manual_weight > 0:
        total_weight = manual_weight
        weight_note = "Вага задана вручну"
    else:
        total_weight = auto_weight
        weight_note = "Вага розрахована автоматично"

    weight_1 = total_weight

    work_per_gram = get_work_price("Каблучка")
    work_cost = total_weight * work_per_gram
    discount = work_cost * (discount_percent / 100)
    work_after_discount = work_cost - discount
    gold_cost = total_weight * GOLD_PRICE

    base_total_without_stones = (
        gold_cost
        + work_after_discount
        + PACKAGING
        + engraving
        + coating_uah
        + delivery
    )

    main_usd, main_uah = get_stone_cost_by_type(
        "Натуральні діаманти",
        main_size,
        main_qty,
        usd_rate,
    )

    small_usd, small_uah = get_stone_cost_by_type(
        "Натуральні діаманти",
        small_size,
        small_qty,
        usd_rate,
    )

    stones_usd = main_usd + small_usd
    stones_uah = main_uah + small_uah
    total = base_total_without_stones + stones_uah

    coating_client = "Без покриття" if coating_usd == 0 else "Родій"
    inserts_text = make_inserts_text(main_size, main_qty, small_size, small_qty)

    technical_text = f"""Курс USD: {usd_rate:.2f} грн

Тип виробу:
Каблучка

{weight_note}:
{weight_1:.2f} г

Загальна вага:
{total_weight:.2f} г

Золото:
{money(gold_cost)} грн

Робота:
{money(work_cost)} грн

Знижка:
-{money(discount)} грн

Робота після знижки:
{money(work_after_discount)} грн

Упаковка:
{money(PACKAGING)} грн

Гравіювання:
{money(engraving)} грн

Покриття:
{money(coating_uah)} грн

Діаманти / каміння:
{money(stones_uah)} грн ({stones_usd}$)

Доставка:
{money(delivery)} грн

=====================
ДО СПЛАТИ:
{money(total)} грн
"""

    variant_totals = {}

    for stone_type in STONE_PRICES_USD.keys():
        _, main_uah_variant = get_stone_cost_by_type(
            stone_type,
            main_size,
            main_qty,
            usd_rate,
        )

        _, small_uah_variant = get_stone_cost_by_type(
            stone_type,
            small_size,
            small_qty,
            usd_rate,
        )

        variant_totals[stone_type] = (
            base_total_without_stones
            + main_uah_variant
            + small_uah_variant
        )

    client_text = f"""Каблучка індивідуального дизайну ⚜️

Біле родоване золото 585 проби 💍
Розмір: {size:g}
Ширина: {width:g} мм
Покриття: {coating_client}
Середня вага виробу: {total_weight:.1f} г
Вставки: {inserts_text}

Середня вартість виробу:
• з натуральними діамантами:
{money100(variant_totals["Натуральні діаманти"])} грн 💎
• з лабораторними діамантами:
{money100(variant_totals["Лабораторні діаманти"])} грн 💎
• з муасанітами:
{money100(variant_totals["Муасаніти"])} грн 💎
"""

    poster_data = {
        "title": "Каблучка індивідуального дизайну ⚜️",
        "gold": "Біле родоване золото 585 проби 💍",
        "sizes": f"Розмір: {size:g}",
        "widths": f"Ширина: {width:g} мм",
        "coating": f"Покриття: {coating_client}",
        "weight": f"Середня вага виробу: {total_weight:.1f} г",
        "price": money100(total),
    }

    return technical_text, client_text, poster_data


st.set_page_config(page_title="Калькулятор Lana & Lona", layout="wide")

if "screen" not in st.session_state:
    st.session_state.screen = "start"

st.markdown(
    """
    <style>
    .main-title {
        text-align: center;
        font-size: 34px;
        font-weight: 700;
        margin-top: 40px;
    }
    textarea {
        font-size: 16px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def go_start():
    st.session_state.screen = "start"


def go_wedding():
    st.session_state.screen = "wedding"


def go_ring():
    st.session_state.screen = "ring"


if st.session_state.screen == "start":
    st.markdown(
        '<div class="main-title">Що потрібно прорахувати?</div>',
        unsafe_allow_html=True,
    )

    st.write("")

    col1, col2, col3 = st.columns([1, 1, 1])

    with col2:
        st.button("Обручки", use_container_width=True, on_click=go_wedding)
        st.button("Каблучка", use_container_width=True, on_click=go_ring)


elif st.session_state.screen == "wedding":
    st.button("← Назад", on_click=go_start)
    st.title("Калькулятор обручок")

    left, right = st.columns([1, 1.4])

    with left:
        st.subheader("Дані для прорахунку")

        design = st.selectbox("Дизайн", ["Вишиванка", "Індивідуальний"])

        st.markdown("### Обручка 1")
        size_1 = st.number_input("Розмір 1", min_value=1.0, value=16.0, step=0.5)
        width_1 = st.number_input("Ширина 1, мм", min_value=0.1, value=5.0, step=0.1)
        thickness_1 = st.number_input("Товщина 1, мм", min_value=0.1, value=1.2, step=0.1)

        use_second_ring = st.checkbox("Додати другу обручку", value=True)

        if use_second_ring:
            st.markdown("### Обручка 2")
            size_2 = st.number_input("Розмір 2", min_value=1.0, value=19.0, step=0.5)
            width_2 = st.number_input("Ширина 2, мм", min_value=0.1, value=5.0, step=0.1)
            thickness_2 = st.number_input("Товщина 2, мм", min_value=0.1, value=1.2, step=0.1)
        else:
            size_2 = 0.0
            width_2 = 0.0
            thickness_2 = 0.0

        st.markdown("### Вставки каміння")
        stone_sizes = list(STONE_PRICES_USD["Натуральні діаманти"].keys())

        ring_stone_enabled = st.checkbox("Додати діаманти в обручку")
        ring_stone_ring = st.selectbox(
            "В яку обручку додати",
            [1, 2] if use_second_ring else [1],
            disabled=not ring_stone_enabled,
        )
        ring_stone_size = st.selectbox(
            "Розмір діаманта",
            stone_sizes,
            index=1,
            disabled=not ring_stone_enabled,
        )
        ring_stone_qty = st.number_input(
            "Кількість діамантів",
            min_value=0,
            value=0,
            step=1,
            disabled=not ring_stone_enabled,
        )

        st.markdown("### Додатково")
        discount_percent = st.selectbox("Знижка, %", [0, 7, 10, 15, 20])
        coating_usd = st.selectbox("Покриття, $", [0, 50, 100, 200])
        engraving = st.selectbox("Гравіювання, грн", [0, 800, 1500])
        delivery = st.number_input("Доставка, грн", min_value=0.0, value=0.0, step=100.0)

        calculate_btn = st.button("РОЗРАХУВАТИ", use_container_width=True)

    with right:
        current_auto_weight_1 = calc_weight(size_1, width_1, thickness_1)
        current_auto_weight_2 = calc_weight(size_2, width_2, thickness_2) if use_second_ring else 0.0

        if calculate_btn:
            st.session_state.wedding_manual_weight_1 = 0.0
            st.session_state.wedding_manual_weight_2 = 0.0

            technical_text, client_text, poster_data = calculate_wedding_rings({
                "design": design,
                "use_second_ring": use_second_ring,
                "size_1": size_1,
                "width_1": width_1,
                "thickness_1": thickness_1,
                "manual_weight_1": 0.0,
                "size_2": size_2,
                "width_2": width_2,
                "thickness_2": thickness_2,
                "manual_weight_2": 0.0,
                "discount_percent": discount_percent,
                "coating_usd": coating_usd,
                "engraving": engraving,
                "delivery": delivery,
                "ring_stone_enabled": ring_stone_enabled,
                "ring_stone_ring": ring_stone_ring,
                "ring_stone_size": ring_stone_size,
                "ring_stone_qty": ring_stone_qty,
            })

            st.session_state.technical_text = technical_text
            st.session_state.client_text = client_text
            st.session_state.poster_data = poster_data

        st.subheader("📊 Технічний розрахунок")
        st.caption("Тут менеджер може виправити вагу вручну і перерахувати ціну.")

        if use_second_ring:
            weight_col1, weight_col2 = st.columns(2)

            with weight_col1:
                manual_weight_1_right = st.number_input(
                    "Вага виробу 1, г",
                    min_value=0.0,
                    value=st.session_state.get("wedding_manual_weight_1", 0.0) or current_auto_weight_1,
                    step=0.1,
                    format="%.2f",
                    key="wedding_weight_input_1",
                )

            with weight_col2:
                manual_weight_2_right = st.number_input(
                    "Вага виробу 2, г",
                    min_value=0.0,
                    value=st.session_state.get("wedding_manual_weight_2", 0.0) or current_auto_weight_2,
                    step=0.1,
                    format="%.2f",
                    key="wedding_weight_input_2",
                )
        else:
            manual_weight_1_right = st.number_input(
                "Вага виробу, г",
                min_value=0.0,
                value=st.session_state.get("wedding_manual_weight_1", 0.0) or current_auto_weight_1,
                step=0.1,
                format="%.2f",
                key="wedding_weight_input_1",
            )
            manual_weight_2_right = 0.0

        if st.button(
            "ПЕРЕРАХУВАТИ ПО ВАЗІ",
            use_container_width=True,
            key="recalculate_wedding_weight",
        ):
            st.session_state.wedding_manual_weight_1 = manual_weight_1_right
            st.session_state.wedding_manual_weight_2 = manual_weight_2_right

            technical_text, client_text, poster_data = calculate_wedding_rings({
                "design": design,
                "use_second_ring": use_second_ring,
                "size_1": size_1,
                "width_1": width_1,
                "thickness_1": thickness_1,
                "manual_weight_1": manual_weight_1_right,
                "size_2": size_2,
                "width_2": width_2,
                "thickness_2": thickness_2,
                "manual_weight_2": manual_weight_2_right,
                "discount_percent": discount_percent,
                "coating_usd": coating_usd,
                "engraving": engraving,
                "delivery": delivery,
                "ring_stone_enabled": ring_stone_enabled,
                "ring_stone_ring": ring_stone_ring,
                "ring_stone_size": ring_stone_size,
                "ring_stone_qty": ring_stone_qty,
            })

            st.session_state.technical_text = technical_text
            st.session_state.client_text = client_text
            st.session_state.poster_data = poster_data

        st.text_area(
            "Технічний текст",
            value=st.session_state.get("technical_text", ""),
            height=420,
        )

        st.subheader("📋 Текст для клієнта")
        client_text = st.session_state.get("client_text", "")
        st.code(client_text, language=None)
        st.caption("Натисни кнопку у правому верхньому куті блоку, щоб скопіювати текст.")

        st.subheader("🖼️ Картинка для клієнта")
        uploaded_product_image = st.file_uploader(
            "Завантаж фото виробу",
            type=["jpg", "jpeg", "png"],
            key="ring_product_image",
        )

        if uploaded_product_image and st.session_state.get("poster_data"):
            if st.button("Згенерувати картинку для клієнта", use_container_width=True, key="generate_ring_poster"):
                image_buffer = generate_client_image(
                    uploaded_product_image,
                    st.session_state.poster_data,
                )
                st.session_state.generated_client_image = image_buffer.getvalue()

        if st.session_state.get("generated_client_image"):
            st.image(st.session_state.generated_client_image, use_container_width=True)
            st.download_button(
                "Завантажити картинку",
                data=st.session_state.generated_client_image,
                file_name="lana_lona_offer.png",
                mime="image/png",
                use_container_width=True,
                key="download_ring_poster",
            )

        st.subheader("🖼️ Картинка для клієнта")
        uploaded_product_image = st.file_uploader(
            "Завантаж фото виробу",
            type=["jpg", "jpeg", "png"],
            key="wedding_product_image",
        )

        if uploaded_product_image and st.session_state.get("poster_data"):
            if st.button("Згенерувати картинку для клієнта", use_container_width=True, key="generate_wedding_poster"):
                image_buffer = generate_client_image(
                    uploaded_product_image,
                    st.session_state.poster_data,
                )
                st.session_state.generated_client_image = image_buffer.getvalue()

        if st.session_state.get("generated_client_image"):
            st.image(st.session_state.generated_client_image, use_container_width=True)
            st.download_button(
                "Завантажити картинку",
                data=st.session_state.generated_client_image,
                file_name="lana_lona_offer.png",
                mime="image/png",
                use_container_width=True,
                key="download_wedding_poster",
            )


elif st.session_state.screen == "ring":
    st.button("← Назад", on_click=go_start)
    st.title("Калькулятор каблучки")

    left, right = st.columns([1, 1.4])

    with left:
        st.subheader("Дані для прорахунку")
        st.info("Для каблучки робота завжди рахується по 6100 грн/г. Дизайн тут не вибирається.")

        size = st.number_input("Розмір", min_value=1.0, value=16.0, step=0.5)
        width = st.number_input("Ширина, мм", min_value=0.1, value=2.5, step=0.1)
        thickness = st.number_input("Товщина, мм", min_value=0.1, value=1.2, step=0.1)

        st.markdown("### Вставки")
        stone_sizes = list(STONE_PRICES_USD["Натуральні діаманти"].keys())

        main_size = st.selectbox("Основний діамант — розмір", stone_sizes, index=0)
        main_qty = st.number_input("Основний діамант — к-сть", min_value=0, value=0, step=1)

        small_size = st.selectbox("Малі діаманти — розмір", stone_sizes, index=0)
        small_qty = st.number_input("Малі діаманти — к-сть", min_value=0, value=0, step=1)

        st.markdown("### Додатково")
        discount_percent = st.selectbox("Знижка, %", [0, 7, 10, 15, 20])
        coating_usd = st.selectbox("Покриття, $", [0, 50, 100, 200])
        engraving = st.selectbox("Гравіювання, грн", [0, 800, 1500])
        delivery = st.number_input("Доставка, грн", min_value=0.0, value=0.0, step=100.0)

        calculate_btn = st.button("РОЗРАХУВАТИ", use_container_width=True)

    with right:
        current_auto_weight = calc_weight(size, width, thickness)

        if calculate_btn:
            st.session_state.ring_manual_weight = 0.0

            technical_text, client_text, poster_data = calculate_ring({
                "size": size,
                "width": width,
                "thickness": thickness,
                "manual_weight": 0.0,
                "main_size": main_size,
                "main_qty": main_qty,
                "small_size": small_size,
                "small_qty": small_qty,
                "discount_percent": discount_percent,
                "coating_usd": coating_usd,
                "engraving": engraving,
                "delivery": delivery,
            })

            st.session_state.technical_text = technical_text
            st.session_state.client_text = client_text
            st.session_state.poster_data = poster_data

        st.subheader("📊 Технічний розрахунок")
        st.caption("Тут менеджер може виправити вагу вручну і перерахувати ціну.")

        manual_weight_right = st.number_input(
            "Вага виробу, г",
            min_value=0.0,
            value=st.session_state.get("ring_manual_weight", 0.0) or current_auto_weight,
            step=0.1,
            format="%.2f",
            key="ring_weight_input",
        )

        if st.button(
            "ПЕРЕРАХУВАТИ ПО ВАГІ",
            use_container_width=True,
            key="recalculate_ring_weight",
        ):
            st.session_state.ring_manual_weight = manual_weight_right

            technical_text, client_text, poster_data = calculate_ring({
                "size": size,
                "width": width,
                "thickness": thickness,
                "manual_weight": manual_weight_right,
                "main_size": main_size,
                "main_qty": main_qty,
                "small_size": small_size,
                "small_qty": small_qty,
                "discount_percent": discount_percent,
                "coating_usd": coating_usd,
                "engraving": engraving,
                "delivery": delivery,
            })

            st.session_state.technical_text = technical_text
            st.session_state.client_text = client_text
            st.session_state.poster_data = poster_data

        st.text_area(
            "Технічний текст",
            value=st.session_state.get("technical_text", ""),
            height=420,
        )

        st.subheader("📋 Текст для клієнта")
        client_text = st.session_state.get("client_text", "")
        st.code(client_text, language=None)
        st.caption("Натисни кнопку у правому верхньому куті блоку, щоб скопіювати текст.")
