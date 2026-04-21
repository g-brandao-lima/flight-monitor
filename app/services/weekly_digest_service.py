"""Weekly digest email service (Phase 29).

Envia resumo semanal por usuario: para cada grupo ativo, preco atual,
delta vs preco de 7 dias atras, indicador de tendencia. Enviado as
tercas 18:00 BRT (21:00 UTC).
"""
import datetime
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import FlightSnapshot, RouteGroup, User
from app.services.alert_service import send_email
from app.services.dashboard_service import format_price_brl

logger = logging.getLogger(__name__)


def build_user_digest(db: Session, user: User) -> dict | None:
    """Monta o digest de um usuario.

    Retorna None se usuario nao tem grupos ativos ou dados insuficientes.
    Retorna dict com {"user": User, "items": [{"group", "price_now", "price_week_ago",
    "delta_pct", "direction", "route"}]}.
    """
    groups = (
        db.query(RouteGroup)
        .filter(RouteGroup.user_id == user.id, RouteGroup.is_active == True)  # noqa: E712
        .all()
    )
    if not groups:
        return None

    items = []
    for group in groups:
        item = _group_digest_item(db, group)
        if item is not None:
            items.append(item)

    if not items:
        return None

    return {"user": user, "items": items}


def _group_digest_item(db: Session, group: RouteGroup) -> dict | None:
    """Monta item do digest para um grupo: preco atual + delta vs 7d atras."""
    now = datetime.datetime.utcnow()
    week_cutoff = now - datetime.timedelta(days=7)

    cheapest_now = (
        db.query(FlightSnapshot)
        .filter(
            FlightSnapshot.route_group_id == group.id,
            FlightSnapshot.origin.in_(group.origins),
            FlightSnapshot.destination.in_(group.destinations),
            FlightSnapshot.collected_at >= now - datetime.timedelta(days=2),
        )
        .order_by(FlightSnapshot.price.asc())
        .first()
    )

    if cheapest_now is None:
        return None

    cheapest_week_ago = (
        db.query(FlightSnapshot)
        .filter(
            FlightSnapshot.route_group_id == group.id,
            FlightSnapshot.origin == cheapest_now.origin,
            FlightSnapshot.destination == cheapest_now.destination,
            FlightSnapshot.collected_at < week_cutoff,
            FlightSnapshot.collected_at >= week_cutoff - datetime.timedelta(days=2),
        )
        .order_by(FlightSnapshot.price.asc())
        .first()
    )

    price_week_ago = cheapest_week_ago.price if cheapest_week_ago else None
    delta_pct = None
    direction = "stable"
    if price_week_ago and price_week_ago > 0:
        delta_pct = (cheapest_now.price - price_week_ago) / price_week_ago * 100
        if delta_pct <= -3:
            direction = "down"
        elif delta_pct >= 3:
            direction = "up"

    return {
        "group": group,
        "price_now": cheapest_now.price,
        "price_week_ago": price_week_ago,
        "delta_pct": delta_pct,
        "direction": direction,
        "route": f"{cheapest_now.origin} -> {cheapest_now.destination}",
        "airline": cheapest_now.airline,
    }


def compose_digest_email(digest: dict) -> MIMEMultipart:
    """Monta o MIMEMultipart do digest."""
    user = digest["user"]
    items = digest["items"]

    subject = f"Orbita: seu resumo semanal ({len(items)} grupos ativos)"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.gmail_sender
    msg["To"] = user.email

    plain = _render_plain(digest)
    html = _render_html(digest)
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    return msg


def _render_plain(digest: dict) -> str:
    user = digest["user"]
    first_name = user.name.split(" ")[0] if user.name else "Viajante"
    lines = [
        f"Ola, {first_name}.",
        "",
        f"Resumo semanal dos {len(digest['items'])} grupos ativos que voce monitora:",
        "",
    ]
    for item in digest["items"]:
        g = item["group"]
        line = f"- {g.name} ({item['route']}): {format_price_brl(item['price_now'])}"
        if item["delta_pct"] is not None:
            arrow = "\u2193" if item["direction"] == "down" else ("\u2191" if item["direction"] == "up" else "\u2192")
            line += f" ({arrow} {item['delta_pct']:+.0f}% vs 7 dias atras)"
        else:
            line += " (sem historico ha 7 dias)"
        lines.append(line)
    lines.append("")
    lines.append(f"Acesse o dashboard: {settings.app_base_url}/")
    lines.append("")
    lines.append("Boas viagens!")
    lines.append("Orbita")
    return "\n".join(lines)


def _render_html(digest: dict) -> str:
    user = digest["user"]
    first_name = user.name.split(" ")[0] if user.name else "Viajante"
    parts = []
    parts.append('<html><body style="font-family:Arial,sans-serif;max-width:640px;margin:0 auto;background:#0b0e14;color:#e2e8f0;padding:32px;">')
    parts.append(f'<h1 style="font-size:22px;margin:0 0 8px;">Ola, {first_name}.</h1>')
    parts.append(f'<p style="color:#94a3b8;font-size:15px;margin:0 0 24px;">Resumo semanal dos seus {len(digest["items"])} grupos ativos.</p>')
    parts.append('<div style="background:#111827;border:1px solid #1e293b;border-radius:12px;padding:20px;">')
    for item in digest["items"]:
        g = item["group"]
        color = {"down": "#34d399", "up": "#f87171", "stable": "#94a3b8"}[item["direction"]]
        arrow = {"down": "&darr;", "up": "&uarr;", "stable": "&rarr;"}[item["direction"]]
        parts.append('<div style="padding:12px 0;border-bottom:1px solid #1f2937;">')
        parts.append(f'<div style="font-weight:600;font-size:15px;">{g.name}</div>')
        parts.append(f'<div style="color:#94a3b8;font-size:13px;margin:2px 0 6px;">{item["route"]} · {item["airline"]}</div>')
        parts.append(f'<div style="font-size:16px;">{format_price_brl(item["price_now"])}')
        if item["delta_pct"] is not None:
            parts.append(f' <span style="color:{color};font-size:13px;margin-left:8px;">{arrow} {item["delta_pct"]:+.0f}% vs 7 dias</span>')
        else:
            parts.append(' <span style="color:#64748b;font-size:13px;margin-left:8px;">sem comparativo</span>')
        parts.append('</div></div>')
    parts.append('</div>')
    parts.append(f'<p style="text-align:center;margin-top:24px;"><a href="{settings.app_base_url}/" style="display:inline-block;background:#0ea5e9;color:white;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600;">Abrir dashboard</a></p>')
    parts.append('<p style="text-align:center;color:#64748b;font-size:12px;margin-top:24px;">Voce recebe este resumo toda terca a noite. Silenciar grupos individuais pelo dashboard.</p>')
    parts.append('</body></html>')
    return "".join(parts)


def run_weekly_digest():
    """Job do scheduler: envia digest para todos os usuarios com grupos ativos."""
    logger.info("Weekly digest job started")
    db = SessionLocal()
    try:
        users = db.query(User).all()
        sent = 0
        for user in users:
            try:
                if not user.email:
                    continue
                digest = build_user_digest(db, user)
                if digest is None:
                    continue
                msg = compose_digest_email(digest)
                send_email(msg)
                sent += 1
                logger.info("Weekly digest sent to user_id=%s", user.id)
            except Exception as e:
                logger.error("Weekly digest failed for user_id=%s: %s", user.id, e, exc_info=True)
        logger.info("Weekly digest job finished: %d emails sent", sent)
    finally:
        db.close()
