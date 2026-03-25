"""Alert service — composicao de email, envio SMTP, token HMAC e silenciamento."""
import hashlib
import hmac
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings
from app.models import DetectedSignal, FlightSnapshot, RouteGroup
from app.services.dashboard_service import format_price_brl

_URGENCY_COLORS = {
    "MAXIMA": "#dc2626",
    "ALTA": "#ea580c",
    "MEDIA": "#ca8a04",
}


def compose_alert_email(signal: DetectedSignal, group: RouteGroup) -> MIMEMultipart:
    """Compoe email de alerta a partir de um sinal detectado.

    Retorna MIMEMultipart com partes text/plain e text/html.
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[{signal.urgency}] {signal.signal_type} - {group.name}"
    msg["From"] = settings.gmail_sender
    msg["To"] = settings.gmail_recipient

    token = generate_silence_token(group.id)
    silence_url = (
        f"{settings.app_base_url}/api/v1/alerts/silence/{token}?group_id={group.id}"
    )

    plain = _render_plain(signal, group, silence_url)
    html = _render_html(signal, group, silence_url)

    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    return msg


def send_email(msg: MIMEMultipart) -> None:
    """Envia email via Gmail SMTP SSL na porta 465."""
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
        server.login(settings.gmail_sender, settings.gmail_app_password)
        server.send_message(msg)


def generate_silence_token(group_id: int) -> str:
    """Gera token HMAC deterministico para silenciamento de um grupo.

    Usa gmail_app_password como segredo; aceitavel para uso single-user.
    Retorna primeiros 32 caracteres do hexdigest SHA-256.
    """
    secret = settings.gmail_app_password.encode()
    message = f"silence:{group_id}".encode()
    return hmac.new(secret, message, hashlib.sha256).hexdigest()[:32]


def verify_silence_token(token: str, group_id: int) -> bool:
    """Verifica se o token de silenciamento e valido para o grupo.

    Usa hmac.compare_digest para prevenir timing attacks.
    """
    expected = generate_silence_token(group_id)
    return hmac.compare_digest(token, expected)


def should_alert(group: RouteGroup) -> bool:
    """Retorna True se o grupo nao esta silenciado no momento.

    Retorna True quando silenced_until e None ou ja expirou.
    """
    if group.silenced_until is None:
        return True
    return datetime.utcnow() > group.silenced_until


# ---------------------------------------------------------------------------
# Private rendering helpers
# ---------------------------------------------------------------------------


def _render_plain(signal: DetectedSignal, group: RouteGroup, silence_url: str) -> str:
    return (
        f"Sinal detectado: {signal.signal_type}\n"
        f"Urgencia: {signal.urgency}\n"
        f"Grupo: {group.name}\n"
        f"Rota: {signal.origin} -> {signal.destination}\n"
        f"Datas: {signal.departure_date} a {signal.return_date}\n"
        f"Preco: R$ {signal.price_at_detection:,.2f}\n"
        f"Detalhes: {signal.details}\n\n"
        f"Silenciar alertas deste grupo por 24h:\n{silence_url}\n"
    )


def _render_html(signal: DetectedSignal, group: RouteGroup, silence_url: str) -> str:
    color = _URGENCY_COLORS.get(signal.urgency, "#6b7280")
    return (
        "<html><body style=\"font-family:Arial,sans-serif;max-width:600px;margin:0 auto;\">"
        f"<div style=\"background:{color};color:white;padding:12px 20px;border-radius:8px 8px 0 0;\">"
        f"<h2 style=\"margin:0;\">{signal.signal_type.replace('_', ' ')}</h2>"
        f"<p style=\"margin:4px 0 0;\">Urgencia: {signal.urgency}</p>"
        "</div>"
        "<div style=\"border:1px solid #e5e7eb;padding:20px;border-radius:0 0 8px 8px;\">"
        f"<p><strong>Grupo:</strong> {group.name}</p>"
        f"<p><strong>Rota:</strong> {signal.origin} &rarr; {signal.destination}</p>"
        f"<p><strong>Datas:</strong> {signal.departure_date} a {signal.return_date}</p>"
        f"<p><strong>Preco atual:</strong> R$ {signal.price_at_detection:,.2f}</p>"
        f"<p><strong>Detalhes:</strong> {signal.details}</p>"
        "<hr style=\"border:none;border-top:1px solid #e5e7eb;\">"
        "<p style=\"text-align:center;\">"
        f"<a href=\"{silence_url}\" style=\"color:#6b7280;font-size:13px;\">"
        "Silenciar alertas deste grupo por 24h"
        "</a></p>"
        "</div></body></html>"
    )


# ---------------------------------------------------------------------------
# Consolidated email (1 email per group)
# ---------------------------------------------------------------------------


def _fmt_date(d) -> str:
    """Formata data para dd/mm/aaaa."""
    return d.strftime("%d/%m/%Y")


def compose_consolidated_email(
    signals: list[DetectedSignal],
    snapshots: list[FlightSnapshot],
    group: RouteGroup,
) -> MIMEMultipart:
    """Compoe email consolidado com rota mais barata, top 3 datas e resumo.

    Retorna MIMEMultipart com partes text/plain e text/html.
    """
    sorted_snaps = sorted(snapshots, key=lambda s: s.price)
    cheapest = sorted_snaps[0]
    top3 = sorted_snaps[:3]

    # Rotas que nao sao a mais barata (para resumo)
    other_routes = sorted_snaps[1:]

    token = generate_silence_token(group.id)
    silence_url = (
        f"{settings.app_base_url}/api/v1/alerts/silence/{token}?group_id={group.id}"
    )

    subject = (
        f"Flight Monitor: {group.name} "
        f"- {format_price_brl(cheapest.price)} (melhor preco)"
    )

    html = _render_consolidated_html(cheapest, top3, other_routes, signals, silence_url, group)
    plain = _render_consolidated_plain(cheapest, top3, other_routes, signals, silence_url, group)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.gmail_sender
    msg["To"] = settings.gmail_recipient

    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    return msg


def _render_consolidated_html(
    cheapest: FlightSnapshot,
    top3: list[FlightSnapshot],
    other_routes: list[FlightSnapshot],
    signals: list[DetectedSignal],
    silence_url: str,
    group: RouteGroup,
) -> str:
    """Monta corpo HTML do email consolidado."""
    parts = []
    parts.append(
        '<html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">'
    )

    # Header com rota mais barata em destaque
    parts.append(
        '<div style="background:#059669;color:white;padding:16px 20px;border-radius:8px 8px 0 0;">'
        f'<h2 style="margin:0;">Melhor preco: {format_price_brl(cheapest.price)}</h2>'
        f'<p style="margin:4px 0 0;">'
        f'{cheapest.origin} &rarr; {cheapest.destination} | {cheapest.airline} | '
        f'{_fmt_date(cheapest.departure_date)} a {_fmt_date(cheapest.return_date)}'
        '</p></div>'
    )

    parts.append('<div style="border:1px solid #e5e7eb;padding:20px;border-radius:0 0 8px 8px;">')

    # Tabela top 3 melhores datas/precos
    parts.append('<h3>Melhores datas</h3>')
    parts.append(
        '<table style="width:100%;border-collapse:collapse;font-size:14px;">'
        '<tr style="background:#f3f4f6;">'
        '<th style="padding:8px;text-align:left;">Rota</th>'
        '<th style="padding:8px;text-align:left;">Ida</th>'
        '<th style="padding:8px;text-align:left;">Volta</th>'
        '<th style="padding:8px;text-align:left;">Cia</th>'
        '<th style="padding:8px;text-align:right;">Preco</th></tr>'
    )
    for snap in top3:
        parts.append(
            f'<tr><td style="padding:8px;">{snap.origin} &rarr; {snap.destination}</td>'
            f'<td style="padding:8px;">{_fmt_date(snap.departure_date)}</td>'
            f'<td style="padding:8px;">{_fmt_date(snap.return_date)}</td>'
            f'<td style="padding:8px;">{snap.airline}</td>'
            f'<td style="padding:8px;text-align:right;">{format_price_brl(snap.price)}</td></tr>'
        )
    parts.append('</table>')

    # Resumo de outras rotas
    if other_routes:
        parts.append('<h3>Outras rotas monitoradas</h3>')
        parts.append('<ul style="font-size:14px;">')
        for snap in other_routes:
            parts.append(
                f'<li>{snap.origin} &rarr; {snap.destination}: '
                f'{format_price_brl(snap.price)}</li>'
            )
        parts.append('</ul>')

    # Sinais detectados
    if signals:
        parts.append('<h3>Sinais detectados</h3>')
        parts.append('<ul style="font-size:14px;">')
        for sig in signals:
            parts.append(
                f'<li>[{sig.urgency}] {sig.signal_type}: '
                f'{sig.origin} &rarr; {sig.destination} '
                f'({_fmt_date(sig.departure_date)} a {_fmt_date(sig.return_date)})</li>'
            )
        parts.append('</ul>')

    # Rodape com link de silenciar
    parts.append('<hr style="border:none;border-top:1px solid #e5e7eb;">')
    parts.append(
        '<p style="text-align:center;">'
        f'<a href="{silence_url}" style="color:#6b7280;font-size:13px;">'
        'Silenciar alertas deste grupo por 24h'
        '</a></p>'
    )

    parts.append('</div></body></html>')
    return ''.join(parts)


def _render_consolidated_plain(
    cheapest: FlightSnapshot,
    top3: list[FlightSnapshot],
    other_routes: list[FlightSnapshot],
    signals: list[DetectedSignal],
    silence_url: str,
    group: RouteGroup,
) -> str:
    """Monta corpo text/plain do email consolidado."""
    lines = []

    lines.append(f"MELHOR PRECO: {format_price_brl(cheapest.price)}")
    lines.append(
        f"Rota: {cheapest.origin} -> {cheapest.destination} | {cheapest.airline}"
    )
    lines.append(
        f"Datas: {_fmt_date(cheapest.departure_date)} a {_fmt_date(cheapest.return_date)}"
    )
    lines.append("")

    lines.append("MELHORES DATAS:")
    for snap in top3:
        lines.append(
            f"  {snap.origin} -> {snap.destination} | "
            f"{_fmt_date(snap.departure_date)} a {_fmt_date(snap.return_date)} | "
            f"{snap.airline} | {format_price_brl(snap.price)}"
        )
    lines.append("")

    if other_routes:
        lines.append("OUTRAS ROTAS:")
        for snap in other_routes:
            lines.append(
                f"  {snap.origin} -> {snap.destination}: {format_price_brl(snap.price)}"
            )
        lines.append("")

    if signals:
        lines.append("SINAIS DETECTADOS:")
        for sig in signals:
            lines.append(
                f"  [{sig.urgency}] {sig.signal_type}: "
                f"{sig.origin} -> {sig.destination}"
            )
        lines.append("")

    lines.append(f"Silenciar alertas por 24h: {silence_url}")

    return "\n".join(lines)
