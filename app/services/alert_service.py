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

_SOURCE_LABELS = {
    "serpapi": "Google Flights",
    "fast_flights": "Google Flights (scraping)",
    "kiwi": "Kiwi.com",
}


def _format_source(source: str | None) -> str:
    if not source:
        return ""
    return _SOURCE_LABELS.get(source, source)


def compose_alert_email(
    signal: DetectedSignal, group: RouteGroup, recipient_email: str | None = None
) -> MIMEMultipart:
    """Compoe email de alerta a partir de um sinal detectado.

    Retorna MIMEMultipart com partes text/plain e text/html.
    recipient_email: email do dono do grupo. Fallback para settings.gmail_recipient.
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[{signal.urgency}] {signal.signal_type} - {group.name}"
    msg["From"] = settings.gmail_sender
    msg["To"] = recipient_email or settings.gmail_recipient

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


def compose_welcome_email(user_name: str, user_email: str) -> MIMEMultipart:
    """Compoe email de boas-vindas para novo usuario."""
    first_name = user_name.split(" ")[0] if user_name else "Viajante"
    dashboard_url = f"{settings.app_base_url}/"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Bem-vindo ao Orbita, {first_name}!"
    msg["From"] = settings.gmail_sender
    msg["To"] = user_email

    plain = (
        f"Olá, {first_name}!\n\n"
        "Sua conta no Orbita foi criada.\n\n"
        "O que o Orbita faz:\n"
        "- Monitora preços de passagens aéreas 24h por dia\n"
        "- Detecta o momento ideal de compra antes que o preço suba\n"
        "- Envia alertas direto no seu email\n\n"
        f"Crie seu primeiro grupo de monitoramento: {dashboard_url}\n\n"
        "Boas viagens!\n"
        "Equipe Orbita"
    )

    html = (
        '<html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;'
        'background:#0b0e14;color:#e2e8f0;padding:32px;">'
        '<div style="text-align:center;margin-bottom:24px;">'
        '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" '
        'fill="none" stroke="#0ea5e9" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M17.8 19.2L16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2'
        'c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 '
        '3.5 5.3c.3.4.8.5 1.3.3l.5-.3c.4-.2.6-.6.5-1.1z"/></svg>'
        '</div>'
        f'<h1 style="text-align:center;font-size:24px;margin:0 0 8px;">Olá, {first_name}!</h1>'
        '<p style="text-align:center;color:#94a3b8;font-size:16px;margin:0 0 32px;">'
        'Sua conta no Orbita foi criada.</p>'
        '<div style="background:#111827;border:1px solid #1e293b;border-radius:12px;padding:24px;'
        'margin-bottom:24px;">'
        '<p style="font-size:14px;color:#94a3b8;margin:0 0 16px;">O que o Orbita faz:</p>'
        '<ul style="font-size:14px;color:#e2e8f0;padding-left:20px;margin:0;">'
        '<li style="margin-bottom:8px;">Monitora preços de passagens aéreas 24h por dia</li>'
        '<li style="margin-bottom:8px;">Detecta o momento ideal de compra antes que o preço suba</li>'
        '<li>Envia alertas direto no seu email</li>'
        '</ul></div>'
        '<div style="text-align:center;">'
        f'<a href="{dashboard_url}" style="display:inline-block;background:linear-gradient(135deg,'
        '#0ea5e9,#3b82f6);color:#fff;font-size:16px;font-weight:700;padding:14px 32px;'
        'border-radius:10px;text-decoration:none;">Criar meu primeiro grupo</a>'
        '</div>'
        '<p style="text-align:center;color:#64748b;font-size:13px;margin-top:32px;">'
        'Boas viagens!<br>Equipe Orbita</p>'
        '</body></html>'
    )

    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    return msg


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


def _price_with_total(price: float, passengers: int) -> tuple[str, str]:
    """Retorna (linha_principal, linha_total_ou_vazio) formatados."""
    pax = max(1, int(passengers or 1))
    main = f"R$ {price:,.2f} por pessoa, ida e volta"
    total = f"Total {pax} passageiros: R$ {price * pax:,.2f}" if pax > 1 else ""
    return main, total


def _render_plain(signal: DetectedSignal, group: RouteGroup, silence_url: str) -> str:
    main, total = _price_with_total(signal.price_at_detection, group.passengers)
    total_line = f"{total}\n" if total else ""
    return (
        f"Sinal detectado: {signal.signal_type}\n"
        f"Urgencia: {signal.urgency}\n"
        f"Grupo: {group.name}\n"
        f"Rota: {signal.origin} -> {signal.destination}\n"
        f"Datas: {signal.departure_date} a {signal.return_date}\n"
        f"Preco: {main}\n"
        f"{total_line}"
        f"Detalhes: {signal.details}\n\n"
        f"Silenciar alertas deste grupo por 24h:\n{silence_url}\n"
    )


def _render_html(signal: DetectedSignal, group: RouteGroup, silence_url: str) -> str:
    color = _URGENCY_COLORS.get(signal.urgency, "#6b7280")
    main, total = _price_with_total(signal.price_at_detection, group.passengers)
    total_html = (
        f"<p style=\"color:#6b7280;font-size:13px;margin:-4px 0 0;\">{total}</p>"
        if total
        else ""
    )
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
        f"<p><strong>Preco atual:</strong> {main}</p>"
        f"{total_html}"
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
    recipient_email: str | None = None,
    db=None,
) -> MIMEMultipart:
    """Compoe email consolidado com rota mais barata, top 3 datas e resumo.

    Retorna MIMEMultipart com partes text/plain e text/html.
    recipient_email: email do dono do grupo. Fallback para settings.gmail_recipient.
    db: Session opcional para enriquecer com contexto historico (Phase 22).
    """
    sorted_snaps = sorted(snapshots, key=lambda s: s.price)
    cheapest = sorted_snaps[0]
    top3 = sorted_snaps[:3]

    # Rotas que nao sao a mais barata (para resumo)
    other_routes = sorted_snaps[1:]

    # Contexto historico (Phase 22): "X% abaixo da media dos ultimos 90 dias"
    historical_ctx = None
    recommendation = None
    if db is not None:
        from app.services.price_prediction_service import build_recommendation_for_group
        from app.services.snapshot_service import get_historical_price_context
        historical_ctx = get_historical_price_context(
            db, cheapest.origin, cheapest.destination
        )
        recommendation = build_recommendation_for_group(db, group, cheapest)

    token = generate_silence_token(group.id)
    silence_url = (
        f"{settings.app_base_url}/api/v1/alerts/silence/{token}?group_id={group.id}"
    )

    subject = _build_subject(cheapest, historical_ctx, group)

    html = _render_consolidated_html(cheapest, top3, other_routes, signals, silence_url, group, historical_ctx, recommendation)
    plain = _render_consolidated_plain(cheapest, top3, other_routes, signals, silence_url, group, historical_ctx, recommendation)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.gmail_sender
    msg["To"] = recipient_email or settings.gmail_recipient

    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    return msg


def _build_subject(cheapest: FlightSnapshot, ctx: dict | None, group: RouteGroup) -> str:
    """Subject line factual (Phase 26).

    Se houver contexto historico com variacao significativa vs media, destaca
    o delta percentual e o preco absoluto. Senao, fallback neutro.

    Exemplos:
    - "GRU-LIS caiu 23% hoje: R$ 3.120 (media 90d R$ 4.050)"
    - "GRU-LIS em R$ 3.120 (media 90d R$ 3.150)"
    - "Orbita: Europa Verao - R$ 3.120" (sem amostras suficientes)
    """
    route = f"{cheapest.origin}-{cheapest.destination}"
    price_str = format_price_brl(cheapest.price)

    if not ctx or ctx.get("avg", 0) <= 0:
        return f"Orbita: {group.name} em {price_str}"

    avg = ctx["avg"]
    avg_str = format_price_brl(avg)
    pct = (cheapest.price - avg) / avg * 100

    if pct <= -10:
        return f"{route} caiu {abs(pct):.0f}% hoje: {price_str} (media 90d {avg_str})"
    if pct <= -5:
        return f"{route} {abs(pct):.0f}% abaixo da media: {price_str} (media 90d {avg_str})"
    if pct >= 10:
        return f"{route} subiu {pct:.0f}%: {price_str} (media 90d {avg_str})"
    return f"{route} em {price_str} (media 90d {avg_str})"


def _format_historical_context(ctx: dict | None, current_price: float) -> str:
    """Retorna frase humana tipo '23% abaixo da media dos ultimos 90 dias (N amostras)'."""
    if not ctx:
        return ""
    avg = ctx["avg"]
    if avg <= 0:
        return ""
    pct = (current_price - avg) / avg * 100
    days = ctx["days"]
    count = ctx["count"]
    if pct <= -5:
        return f"{abs(pct):.0f}% abaixo da media dos ultimos {days} dias ({count} amostras)"
    if pct >= 5:
        return f"{pct:.0f}% acima da media dos ultimos {days} dias ({count} amostras)"
    return f"Em linha com a media dos ultimos {days} dias ({count} amostras)"


def _render_consolidated_html(
    cheapest: FlightSnapshot,
    top3: list[FlightSnapshot],
    other_routes: list[FlightSnapshot],
    signals: list[DetectedSignal],
    silence_url: str,
    group: RouteGroup,
    historical_ctx: dict | None = None,
    recommendation=None,
) -> str:
    """Monta corpo HTML do email consolidado."""
    parts = []
    parts.append(
        '<html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">'
    )

    pax = max(1, int(group.passengers or 1))

    # Header com rota mais barata em destaque
    header_sub = (
        f'<p style="margin:4px 0 0;">'
        f'{cheapest.origin} &rarr; {cheapest.destination} | {cheapest.airline} | '
        f'{_fmt_date(cheapest.departure_date)} a {_fmt_date(cheapest.return_date)}'
        '</p>'
        '<p style="margin:4px 0 0;font-size:13px;opacity:0.85;">por pessoa, ida e volta'
    )
    if pax > 1:
        header_sub += (
            f' &middot; total {pax} passageiros: {format_price_brl(cheapest.price * pax)}'
        )
    header_sub += '</p>'
    source_label = _format_source(cheapest.source)
    source_html = (
        f'<p style="margin:4px 0 0;font-size:11px;opacity:0.75;letter-spacing:0.3px;text-transform:uppercase;">Fonte: {source_label}</p>'
        if source_label else ''
    )
    context_phrase = _format_historical_context(historical_ctx, cheapest.price)
    context_html = (
        f'<p style="margin:8px 0 0;padding:6px 10px;background:rgba(255,255,255,0.15);border-radius:6px;font-size:13px;font-weight:600;">{context_phrase}</p>'
        if context_phrase else ''
    )
    label_html = '<p style="margin:4px 0 0;font-size:12px;opacity:0.9;font-weight:600;">Preço de referência Google Flights</p>'
    disclaimer_html = '<p style="margin:8px 0 0;font-size:11px;opacity:0.8;font-style:italic;">Pode divergir até 5% do valor final; bagagem e taxas não incluídas.</p>'
    parts.append(
        '<div style="background:#059669;color:white;padding:16px 20px;border-radius:8px 8px 0 0;">'
        f'<h2 style="margin:0;">Melhor preco: {format_price_brl(cheapest.price)}</h2>'
        + label_html + header_sub + source_html + context_html + disclaimer_html +
        '</div>'
    )

    if recommendation is not None:
        rec_colors = {
            "COMPRE": ("#059669", "#ECFDF5"),
            "AGUARDE": ("#B45309", "#FFFBEB"),
            "MONITORAR": ("#475569", "#F1F5F9"),
        }
        accent, bg_color = rec_colors.get(recommendation.action, ("#475569", "#F1F5F9"))
        deadline_html = ""
        if recommendation.deadline:
            deadline_html = (
                f'<div style="font-size:12px;font-family:monospace;margin-top:6px;opacity:0.85;">'
                f'Ate {_fmt_date(recommendation.deadline)}</div>'
            )
        parts.append(
            f'<div style="margin:16px 0 0;padding:14px 18px;background:{bg_color};'
            f'border-left:4px solid {accent};border-radius:6px;color:{accent};">'
            f'<div style="font-size:12px;font-weight:700;letter-spacing:0.1em;">RECOMENDACAO: {recommendation.action}</div>'
            f'<div style="font-size:14px;color:#0f172a;margin-top:4px;">{recommendation.reason}</div>'
            f'{deadline_html}'
            '</div>'
        )

    parts.append('<div style="border:1px solid #e5e7eb;padding:20px;border-radius:0 0 8px 8px;">')

    # CTA "Comprar agora" via nosso redirect tracked /comprar/ (registra
    # clique antes de redirecionar pro Aviasales com marker).
    buy_url = (
        f"{settings.app_base_url.rstrip('/')}/comprar/"
        f"{cheapest.origin}-{cheapest.destination}"
        f"?dep={cheapest.departure_date.isoformat()}"
        f"&ret={cheapest.return_date.isoformat()}"
        f"&pax={pax}&source=email"
    )
    parts.append(
        '<div style="text-align:center;margin-bottom:20px;">'
        f'<a href="{buy_url}" style="display:inline-block;background:linear-gradient(135deg,#6366F1,#22D3EE);'
        'color:#fff;font-weight:700;padding:14px 32px;border-radius:10px;text-decoration:none;font-size:15px;">'
        f'Comprar por {format_price_brl(cheapest.price)} &rarr;'
        '</a>'
        '<p style="color:#6b7280;font-size:11px;margin:8px 0 0;font-style:italic;">'
        'Redireciona para Aviasales com datas já preenchidas. Recebemos comissão sem custo extra.'
        '</p>'
        '</div>'
    )

    # Tabela top 3 melhores datas/precos
    parts.append('<h3>Melhores datas</h3>')
    parts.append(
        '<p style="color:#6b7280;font-size:13px;margin:-8px 0 8px;">Precos por pessoa, ida e volta'
        + (f' &middot; multiplique por {pax} para o total' if pax > 1 else '')
        + '</p>'
    )
    price_header = 'Preco (total)' if pax > 1 else 'Preco'
    parts.append(
        '<table style="width:100%;border-collapse:collapse;font-size:14px;">'
        '<tr style="background:#f3f4f6;">'
        '<th style="padding:8px;text-align:left;">Rota</th>'
        '<th style="padding:8px;text-align:left;">Ida</th>'
        '<th style="padding:8px;text-align:left;">Volta</th>'
        '<th style="padding:8px;text-align:left;">Cia</th>'
        f'<th style="padding:8px;text-align:right;">{price_header}</th></tr>'
    )
    for snap in top3:
        price_cell = format_price_brl(snap.price)
        if pax > 1:
            price_cell = (
                f'{price_cell}<br>'
                f'<span style="color:#6b7280;font-size:12px;">'
                f'{format_price_brl(snap.price * pax)}</span>'
            )
        parts.append(
            f'<tr><td style="padding:8px;">{snap.origin} &rarr; {snap.destination}</td>'
            f'<td style="padding:8px;">{_fmt_date(snap.departure_date)}</td>'
            f'<td style="padding:8px;">{_fmt_date(snap.return_date)}</td>'
            f'<td style="padding:8px;">{snap.airline}</td>'
            f'<td style="padding:8px;text-align:right;">{price_cell}</td></tr>'
        )
    parts.append('</table>')

    # Resumo de outras rotas
    if other_routes:
        parts.append('<h3>Outras rotas monitoradas</h3>')
        parts.append('<ul style="font-size:14px;">')
        for snap in other_routes:
            total_str = (
                f' (total {format_price_brl(snap.price * pax)})' if pax > 1 else ''
            )
            parts.append(
                f'<li>{snap.origin} &rarr; {snap.destination}: '
                f'{format_price_brl(snap.price)} por pessoa{total_str}</li>'
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
    historical_ctx: dict | None = None,
    recommendation=None,
) -> str:
    """Monta corpo text/plain do email consolidado."""
    pax = max(1, int(group.passengers or 1))
    pax_suffix = f" (total {pax} pax: {format_price_brl(cheapest.price * pax)})" if pax > 1 else ""
    lines = []

    lines.append(f"MELHOR PRECO: {format_price_brl(cheapest.price)} por pessoa, ida e volta{pax_suffix}")
    if recommendation is not None:
        lines.append(f"RECOMENDACAO: {recommendation.action}: {recommendation.reason}")
    lines.append("Preço de referência Google Flights")
    lines.append("(Pode divergir até 5% do valor final; bagagem e taxas não incluídas)")
    lines.append(
        f"Rota: {cheapest.origin} -> {cheapest.destination} | {cheapest.airline}"
    )
    lines.append(
        f"Datas: {_fmt_date(cheapest.departure_date)} a {_fmt_date(cheapest.return_date)}"
    )
    if cheapest.source:
        lines.append(f"Fonte: {_format_source(cheapest.source)}")
    context_phrase = _format_historical_context(historical_ctx, cheapest.price)
    if context_phrase:
        lines.append(f"Contexto: {context_phrase}")

    # CTA Comprar agora via /comprar/ tracked redirect
    buy_url = (
        f"{settings.app_base_url.rstrip('/')}/comprar/"
        f"{cheapest.origin}-{cheapest.destination}"
        f"?dep={cheapest.departure_date.isoformat()}"
        f"&ret={cheapest.return_date.isoformat()}"
        f"&pax={pax}&source=email"
    )
    lines.append("")
    lines.append(f"Comprar agora: {buy_url}")
    lines.append("")

    lines.append(f"MELHORES DATAS (precos por pessoa, ida e volta{', total para ' + str(pax) + ' pax entre parenteses' if pax > 1 else ''}):")
    for snap in top3:
        total_str = f" ({format_price_brl(snap.price * pax)} total)" if pax > 1 else ""
        lines.append(
            f"  {snap.origin} -> {snap.destination} | "
            f"{_fmt_date(snap.departure_date)} a {_fmt_date(snap.return_date)} | "
            f"{snap.airline} | {format_price_brl(snap.price)}{total_str}"
        )
    lines.append("")

    if other_routes:
        lines.append("OUTRAS ROTAS:")
        for snap in other_routes:
            total_str = f" (total {format_price_brl(snap.price * pax)})" if pax > 1 else ""
            lines.append(
                f"  {snap.origin} -> {snap.destination}: {format_price_brl(snap.price)} por pessoa{total_str}"
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
