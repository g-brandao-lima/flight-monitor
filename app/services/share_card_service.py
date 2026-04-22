"""Helpers de geracao de imagem com Pillow.

Originalmente hospedava um card PNG "compartilhavel" por grupo
(feature desabilitada). Hoje so expoe primitivas (_load_font,
_gradient_background) reaproveitadas por public_share_card_service.py
pra gerar a OG image das paginas publicas de rota.
"""
from PIL import Image, ImageDraw, ImageFont


BG_TOP = (11, 14, 20)
BG_BOTTOM = (17, 24, 39)

CARD_W, CARD_H = 1200, 630


def _load_font(
    size: int, bold: bool = False
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Carrega TrueType do sistema com fallback seguro."""
    candidates = [
        "arialbd.ttf" if bold else "arial.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "Helvetica-Bold.ttc" if bold else "Helvetica.ttc",
    ]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def _gradient_background(img: Image.Image) -> None:
    """Pinta gradiente vertical top -> bottom."""
    top_r, top_g, top_b = BG_TOP
    bot_r, bot_g, bot_b = BG_BOTTOM
    draw = ImageDraw.Draw(img)
    for y in range(CARD_H):
        t = y / CARD_H
        r = int(top_r + (bot_r - top_r) * t)
        g = int(top_g + (bot_g - top_g) * t)
        b = int(top_b + (bot_b - top_b) * t)
        draw.line([(0, y), (CARD_W, y)], fill=(r, g, b))
