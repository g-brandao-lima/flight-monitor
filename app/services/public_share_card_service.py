"""Open Graph image 1200x630 para pagina publica de rota (SEO-03)."""
from io import BytesIO

from PIL import Image, ImageDraw

from app.services.dashboard_service import format_price_brl
from app.services.share_card_service import _gradient_background, _load_font

OG_W, OG_H = 1200, 630
BG = (11, 14, 20)
ACCENT = (14, 165, 233)
GREEN = (34, 197, 94)
RED = (239, 68, 68)
TEXT = (226, 232, 240)
MUTED = (148, 163, 184)


def build_public_og_card(
    origin: str,
    dest: str,
    current_price: float | None,
    median_180d: float | None,
    origin_city: str,
    dest_city: str,
) -> bytes:
    img = Image.new("RGB", (OG_W, OG_H), BG)
    _gradient_background(img)
    draw = ImageDraw.Draw(img)

    f_brand = _load_font(32, bold=True)
    f_route = _load_font(64, bold=True)
    f_cities = _load_font(28)
    f_price = _load_font(140, bold=True)
    f_sub = _load_font(26)

    draw.text((60, 50), "FLIGHT MONITOR", font=f_brand, fill=ACCENT)
    draw.text((60, 140), f"{origin}  \u2192  {dest}", font=f_route, fill=TEXT)
    draw.text((60, 220), f"{origin_city} para {dest_city}", font=f_cities, fill=MUTED)

    if current_price:
        price_text = format_price_brl(current_price)
        color = GREEN
        if median_180d and current_price > median_180d * 1.05:
            color = RED
        draw.text((60, 300), price_text, font=f_price, fill=color)
        sub = "preco de referencia"
        if median_180d:
            delta_pct = round((current_price - median_180d) / median_180d * 100)
            sign = "+" if delta_pct >= 0 else ""
            sub += f"   \u00b7   {sign}{delta_pct}% vs mediana 180d"
        draw.text((64, 470), sub, font=f_sub, fill=MUTED)
    else:
        draw.text((60, 340), "Monitore este preco", font=f_cities, fill=TEXT)

    draw.text((60, OG_H - 60), "orbita-flights.fly.dev", font=f_sub, fill=MUTED)

    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
