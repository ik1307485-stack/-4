import streamlit as st
import streamlit.components.v1 as components
import requests
import base64
import html
import io
from PIL import Image


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

    poster_price = money100(variant_totals["Натуральні діаманти"]) if ring_stone_qty > 0 else money100(total)
    poster_data = {
        "title": title.replace("⚜️", "").strip(),
        "gold": "Біле родоване золото 585 проби",
        "sizes": client_sizes_text.replace("Розміри: ", "").replace("Розмір: ", ""),
        "width": client_width_text.replace("Ширина: ", ""),
        "coating": coating_client,
        "weight": f"{total_weight:.1f} г",
        "price": poster_price,
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
        "title": "Каблучка індивідуального дизайну",
        "gold": "Біле родоване золото 585 проби",
        "sizes": f"{size:g}",
        "width": f"{width:g} мм",
        "coating": coating_client,
        "weight": f"{total_weight:.1f} г",
        "price": money100(variant_totals["Натуральні діаманти"]),
    }

    return technical_text, client_text, poster_data


def prepare_product_image_data_url(uploaded_file):
    if uploaded_file is None:
        return ""
    uploaded_file.seek(0)
    img = Image.open(uploaded_file).convert("RGBA")
    img.thumbnail((900, 700), Image.LANCZOS)
    pixels = img.load()
    img_w, img_h = img.size
    for y in range(img_h):
        for x in range(img_w):
            r, g, b, a = pixels[x, y]
            if r > 235 and g > 235 and b > 235:
                pixels[x, y] = (255, 255, 255, 0)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return "data:image/png;base64," + encoded


def poster_html(uploaded_file, poster_data):
    image_data_url = prepare_product_image_data_url(uploaded_file)
    data = {
        "title": html.escape(poster_data.get("title", "")),
        "gold": html.escape(poster_data.get("gold", "Біле родоване золото 585 проби")),
        "sizes": html.escape(poster_data.get("sizes", "")),
        "width_text": html.escape(poster_data.get("width", "")),
        "coating": html.escape(poster_data.get("coating", "")),
        "weight": html.escape(poster_data.get("weight", "")),
        "price": html.escape(poster_data.get("price", "")),
        "image_data_url": image_data_url,
    }
    return """
<!DOCTYPE html>
<html lang="uk">
<head>
<meta charset="UTF-8" />
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
<style>
* {{ box-sizing: border-box; }}
body {{ margin:0; padding:24px; background:#111; font-family: Georgia, 'Times New Roman', 'DejaVu Serif', serif; color:#f4efe8; }}
.wrap {{ width:100%; display:flex; flex-direction:column; align-items:center; gap:16px; }}
#poster {{ width:900px; height:1125px; background: radial-gradient(circle at 50% 38%, rgba(150,95,55,0.20), transparent 34%), radial-gradient(circle at 50% 52%, rgba(255,255,255,0.08), transparent 28%), linear-gradient(180deg,#050505 0%,#0b0b0b 55%,#030303 100%); border:1px solid rgba(191,124,78,.55); position:relative; overflow:hidden; padding:54px 58px 40px; box-shadow:0 30px 80px rgba(0,0,0,.65); }}
#poster:before {{ content:''; position:absolute; inset:26px; border:1px solid rgba(191,124,78,.32); pointer-events:none; }}
.title {{ position:relative; z-index:2; text-align:center; color:#d4905d; font-size:46px; line-height:1.08; font-weight:700; letter-spacing:1.2px; text-transform:uppercase; margin-top:8px; }}
.subtitle {{ position:relative; z-index:2; text-align:center; font-size:27px; line-height:1.25; margin-top:20px; color:#f7efe6; letter-spacing:.4px; }}
.product-area {{ position:relative; height:445px; margin-top:24px; display:flex; align-items:center; justify-content:center; }}
.glow {{ position:absolute; width:620px; height:260px; background:radial-gradient(ellipse at center, rgba(255,255,255,.18), rgba(212,144,93,.10) 36%, transparent 70%); filter:blur(20px); top:105px; }}
.product-img {{ position:relative; z-index:2; max-width:720px; max-height:430px; object-fit:contain; filter:drop-shadow(0 28px 34px rgba(0,0,0,.65)); }}
.info-grid {{ position:relative; z-index:2; display:grid; grid-template-columns:repeat(5,1fr); border-top:2px solid rgba(191,124,78,.75); border-bottom:2px solid rgba(191,124,78,.75); margin-top:8px; padding:22px 0; }}
.cell {{ min-height:112px; padding:0 10px; text-align:center; display:flex; flex-direction:column; align-items:center; justify-content:center; border-left:1px solid rgba(191,124,78,.42); }}
.cell:first-child {{ border-left:none; }}
.label {{ color:#d4905d; font-size:18px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; margin-bottom:12px; }}
.value {{ color:#fff7ef; font-size:23px; line-height:1.16; font-weight:600; }}
.price-label {{ position:relative; z-index:2; text-align:center; color:#d4905d; font-size:30px; font-weight:700; letter-spacing:.8px; margin-top:34px; text-transform:uppercase; }}
.price {{ position:relative; z-index:2; text-align:center; color:#d4905d; font-size:72px; line-height:1; font-weight:800; margin-top:12px; letter-spacing:1px; }}
.brand {{ position:absolute; bottom:28px; left:0; right:0; text-align:center; color:rgba(255,255,255,.58); font-size:24px; letter-spacing:3px; font-weight:600; }}
.download {{ width:900px; border:0; border-radius:12px; padding:16px 20px; background:#d4905d; color:#111; font-size:20px; font-weight:800; cursor:pointer; }}
.hint {{ width:900px; color:#ccc; font-family:Arial,sans-serif; font-size:14px; text-align:center; }}
</style>
</head>
<body>
<div class="wrap">
<div id="poster">
<div class="title">{title}</div>
<div class="subtitle">{gold}</div>
<div class="product-area"><div class="glow"></div><img class="product-img" src="{image_data_url}" /></div>
<div class="info-grid">
<div class="cell"><div class="label">Золото</div><div class="value">585 проба</div></div>
<div class="cell"><div class="label">Розміри</div><div class="value">{sizes}</div></div>
<div class="cell"><div class="label">Ширина</div><div class="value">{width_text}</div></div>
<div class="cell"><div class="label">Покриття</div><div class="value">{coating}</div></div>
<div class="cell"><div class="label">Вага</div><div class="value">{weight}</div></div>
</div>
<div class="price-label">Середня вартість виробу:</div>
<div class="price">{price} грн</div>
<div class="brand">LANA &amp; LONA</div>
</div>
<button class="download" onclick="downloadPoster()">Завантажити PNG</button>
<div class="hint">Якщо кнопка не спрацювала з першого разу — натисни ще раз після повного завантаження фото.</div>
</div>
<script>
async function downloadPoster() {{
 const poster = document.getElementById('poster');
 const canvas = await html2canvas(poster, {{backgroundColor:null, scale:2, useCORS:true}});
 const link = document.createElement('a');
 link.download = 'lana_lona_offer.png';
 link.href = canvas.toDataURL('image/png');
 link.click();
}}
</script>
</body>
</html>
""".format(**data)


def render_poster_block(uploaded_file, poster_data):
    if uploaded_file is None:
        st.info("Завантаж фото виробу, щоб створити картинку для клієнта.")
        return
    components.html(poster_html(uploaded_file, poster_data), height=1280, scrolling=True)



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
            key="wedding_product_image" if st.session_state.screen == "wedding" else "ring_product_image",
        )
        if st.session_state.get("poster_data"):
            render_poster_block(uploaded_product_image, st.session_state.poster_data)


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

        st.subheader("🖼️ Картинка для клієнта")
        uploaded_product_image = st.file_uploader(
            "Завантаж фото виробу",
            type=["jpg", "jpeg", "png"],
            key="wedding_product_image" if st.session_state.screen == "wedding" else "ring_product_image",
        )
        if st.session_state.get("poster_data"):
            render_poster_block(uploaded_product_image, st.session_state.poster_data)
