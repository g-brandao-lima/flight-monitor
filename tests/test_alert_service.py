"""Testes unitarios para app/services/alert_service.py — TDD RED phase."""
import datetime
import unittest.mock

import pytest

from app.models import DetectedSignal, RouteGroup
from app.services.alert_service import (
    compose_alert_email,
    compose_consolidated_email,
    generate_silence_token,
    send_email,
    should_alert,
    verify_silence_token,
)
from app.models import FlightSnapshot


# ---------------------------------------------------------------------------
# Helpers / fixtures locais
# ---------------------------------------------------------------------------


def _make_group(
    group_id: int = 1,
    name: str = "GRU-JFK Janeiro",
    silenced_until: datetime.datetime | None = None,
) -> unittest.mock.MagicMock:
    group = unittest.mock.MagicMock(spec=RouteGroup)
    group.id = group_id
    group.name = name
    group.silenced_until = silenced_until
    return group


def _make_signal(
    signal_type: str = "BALDE_FECHANDO",
    urgency: str = "ALTA",
    details: str = "Classe K: 3 -> 1 assentos",
    origin: str = "GRU",
    destination: str = "JFK",
    departure_date: datetime.date = datetime.date(2026, 1, 15),
    return_date: datetime.date = datetime.date(2026, 1, 22),
    price_at_detection: float = 3500.00,
    route_group_id: int = 1,
) -> unittest.mock.MagicMock:
    signal = unittest.mock.MagicMock(spec=DetectedSignal)
    signal.signal_type = signal_type
    signal.urgency = urgency
    signal.details = details
    signal.origin = origin
    signal.destination = destination
    signal.departure_date = departure_date
    signal.return_date = return_date
    signal.price_at_detection = price_at_detection
    signal.route_group_id = route_group_id
    return signal


# ---------------------------------------------------------------------------
# Tests — compose_alert_email
# ---------------------------------------------------------------------------


def test_compose_email_subject_contains_urgency_and_signal_type():
    # Arrange
    group = _make_group()
    signal = _make_signal(signal_type="BALDE_FECHANDO", urgency="ALTA")

    # Act
    msg = compose_alert_email(signal, group)

    # Assert
    subject = msg["Subject"]
    assert "[ALTA]" in subject
    assert "BALDE_FECHANDO" in subject


def test_compose_email_body_contains_group_name():
    # Arrange
    group = _make_group(name="GRU-JFK Janeiro")
    signal = _make_signal()

    # Act
    msg = compose_alert_email(signal, group)

    # Assert — decodifica partes base64 antes de inspecionar
    body = _decode_msg_body(msg)
    assert "GRU-JFK Janeiro" in body


def _decode_msg_body(msg) -> str:
    """Decodifica todas as partes do MIMEMultipart em texto plano."""
    parts = []
    for part in msg.walk():
        payload = part.get_payload(decode=True)
        if payload:
            parts.append(payload.decode("utf-8", errors="replace"))
    return "\n".join(parts)


def test_compose_email_body_contains_route_info():
    # Arrange
    group = _make_group()
    signal = _make_signal(
        origin="GRU",
        destination="JFK",
        departure_date=datetime.date(2026, 1, 15),
        return_date=datetime.date(2026, 1, 22),
        price_at_detection=3500.00,
    )

    # Act
    msg = compose_alert_email(signal, group)

    # Assert — decodifica partes base64 antes de inspecionar
    body = _decode_msg_body(msg)
    assert "GRU" in body
    assert "JFK" in body
    assert "2026-01-15" in body
    assert "2026-01-22" in body
    assert "3" in body and "500" in body  # R$ 3,500.00 formato BRL


def test_compose_email_body_contains_silence_link():
    # Arrange
    group = _make_group(group_id=5)
    signal = _make_signal()

    # Act
    msg = compose_alert_email(signal, group)

    # Assert — decodifica partes base64 antes de inspecionar
    body = _decode_msg_body(msg)
    assert "/api/v1/alerts/silence/" in body


def test_compose_email_plain_text_fallback():
    # Arrange
    group = _make_group()
    signal = _make_signal(signal_type="BALDE_REABERTO", urgency="MAXIMA")

    # Act
    msg = compose_alert_email(signal, group)

    # Assert — deve ter parte text/plain com info do sinal
    plain_part = None
    for part in msg.walk():
        if part.get_content_type() == "text/plain":
            plain_part = part.get_payload(decode=True).decode("utf-8")
            break

    assert plain_part is not None
    assert "BALDE_REABERTO" in plain_part or "GRU" in plain_part


# ---------------------------------------------------------------------------
# Tests — send_email
# ---------------------------------------------------------------------------


def test_send_email_calls_smtp_ssl():
    # Arrange
    group = _make_group()
    signal = _make_signal()
    msg = None

    with unittest.mock.patch("smtplib.SMTP_SSL") as mock_ssl:
        mock_server = unittest.mock.MagicMock()
        mock_ssl.return_value.__enter__ = unittest.mock.MagicMock(
            return_value=mock_server
        )
        mock_ssl.return_value.__exit__ = unittest.mock.MagicMock(return_value=False)

        # Act
        send_email(unittest.mock.MagicMock())

        # Assert
        mock_ssl.assert_called_once()
        call_args = mock_ssl.call_args
        assert call_args[0][0] == "smtp.gmail.com"
        assert call_args[0][1] == 465


def test_send_email_uses_timeout():
    # Arrange
    with unittest.mock.patch("smtplib.SMTP_SSL") as mock_ssl:
        mock_server = unittest.mock.MagicMock()
        mock_ssl.return_value.__enter__ = unittest.mock.MagicMock(
            return_value=mock_server
        )
        mock_ssl.return_value.__exit__ = unittest.mock.MagicMock(return_value=False)

        # Act
        send_email(unittest.mock.MagicMock())

        # Assert
        call_kwargs = mock_ssl.call_args[1]
        assert call_kwargs.get("timeout") == 30


# ---------------------------------------------------------------------------
# Tests — generate_silence_token
# ---------------------------------------------------------------------------


def test_generate_silence_token_deterministic():
    # Arrange / Act
    token1 = generate_silence_token(1)
    token2 = generate_silence_token(1)

    # Assert
    assert token1 == token2
    assert isinstance(token1, str)
    assert len(token1) > 0


def test_generate_silence_token_different_groups():
    # Arrange / Act
    token1 = generate_silence_token(1)
    token2 = generate_silence_token(2)

    # Assert
    assert token1 != token2


# ---------------------------------------------------------------------------
# Tests — verify_silence_token
# ---------------------------------------------------------------------------


def test_verify_silence_token_valid():
    # Arrange
    group_id = 42
    token = generate_silence_token(group_id)

    # Act
    result = verify_silence_token(token, group_id)

    # Assert
    assert result is True


def test_verify_silence_token_invalid():
    # Arrange
    group_id = 42

    # Act
    result = verify_silence_token("token_falso_invalido_xpto", group_id)

    # Assert
    assert result is False


# ---------------------------------------------------------------------------
# Tests — should_alert
# ---------------------------------------------------------------------------


def test_should_alert_no_silence():
    # Arrange — grupo sem silenciamento
    group = _make_group(silenced_until=None)

    # Act
    result = should_alert(group)

    # Assert
    assert result is True


def test_should_alert_silenced():
    # Arrange — grupo silenciado ate o futuro
    future = datetime.datetime.utcnow() + datetime.timedelta(hours=12)
    group = _make_group(silenced_until=future)

    # Act
    result = should_alert(group)

    # Assert
    assert result is False


def test_should_alert_expired():
    # Arrange — silenciamento expirado (data no passado)
    past = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
    group = _make_group(silenced_until=past)

    # Act
    result = should_alert(group)

    # Assert
    assert result is True


# ---------------------------------------------------------------------------
# Helpers — compose_consolidated_email
# ---------------------------------------------------------------------------


def _make_snapshot(
    origin: str = "GRU",
    destination: str = "JFK",
    departure_date: datetime.date = datetime.date(2026, 1, 15),
    return_date: datetime.date = datetime.date(2026, 1, 22),
    price: float = 3500.00,
    airline: str = "LA",
    route_group_id: int = 1,
) -> unittest.mock.MagicMock:
    snap = unittest.mock.MagicMock(spec=FlightSnapshot)
    snap.origin = origin
    snap.destination = destination
    snap.departure_date = departure_date
    snap.return_date = return_date
    snap.price = price
    snap.airline = airline
    snap.route_group_id = route_group_id
    return snap


def _make_signals_list(count: int = 1) -> list[unittest.mock.MagicMock]:
    signals = []
    for i in range(count):
        sig = _make_signal(
            signal_type="BALDE_FECHANDO" if i % 2 == 0 else "PRECO_BAIXO",
            urgency="ALTA" if i % 2 == 0 else "MEDIA",
            price_at_detection=3500.00 + i * 100,
        )
        signals.append(sig)
    return signals


# ---------------------------------------------------------------------------
# Tests — compose_consolidated_email
# ---------------------------------------------------------------------------


def test_consolidated_email_subject_contains_group_name_and_best_price():
    """Sem contexto historico (db=None), subject usa fallback neutro."""
    # Arrange
    group = _make_group(name="GRU-MIA Fevereiro")
    snapshots = [
        _make_snapshot(price=4200.00),
        _make_snapshot(price=2800.50, destination="MIA"),
        _make_snapshot(price=3500.00),
    ]
    signals = _make_signals_list(1)

    # Act
    msg = compose_consolidated_email(signals, snapshots, group)

    # Assert: Phase 26 troca subject para fallback neutro com nome + preco
    subject = msg["Subject"]
    assert "GRU-MIA Fevereiro" in subject
    assert "R$ 2.800,50" in subject


def test_consolidated_email_cheapest_route_in_body():
    # Arrange
    group = _make_group(name="GRU-JFK Janeiro")
    cheapest = _make_snapshot(
        origin="GRU",
        destination="JFK",
        price=2500.00,
        airline="LA",
        departure_date=datetime.date(2026, 3, 10),
        return_date=datetime.date(2026, 3, 20),
    )
    other = _make_snapshot(price=4000.00, origin="GIG", destination="JFK")
    snapshots = [other, cheapest]
    signals = _make_signals_list(1)

    # Act
    msg = compose_consolidated_email(signals, snapshots, group)

    # Assert
    body = _decode_msg_body(msg)
    assert "GRU" in body
    assert "JFK" in body
    assert "R$ 2.500,00" in body
    assert "LA" in body
    assert "10/03/2026" in body
    assert "20/03/2026" in body


def test_consolidated_email_top3_dates_table():
    # Arrange
    group = _make_group()
    snapshots = [
        _make_snapshot(price=5000.00, departure_date=datetime.date(2026, 1, 10), return_date=datetime.date(2026, 1, 17)),
        _make_snapshot(price=2800.00, departure_date=datetime.date(2026, 1, 15), return_date=datetime.date(2026, 1, 22)),
        _make_snapshot(price=3200.00, departure_date=datetime.date(2026, 1, 20), return_date=datetime.date(2026, 1, 27)),
        _make_snapshot(price=4500.00, departure_date=datetime.date(2026, 1, 25), return_date=datetime.date(2026, 2, 1)),
    ]
    signals = _make_signals_list(1)

    # Act
    msg = compose_consolidated_email(signals, snapshots, group)

    # Assert — tabela com top 3 ordenadas por preco crescente
    body = _decode_msg_body(msg)
    # Deve conter os 3 mais baratos: 2800, 3200, 5000
    assert "R$ 2.800,00" in body
    assert "R$ 3.200,00" in body
    assert "R$ 5.000,00" in body
    # O quarto (4500) pode aparecer no resumo, mas os 3 primeiros devem estar na tabela
    # Verificar que as datas estao em formato brasileiro
    assert "15/01/2026" in body
    assert "20/01/2026" in body


def test_consolidated_email_other_routes_summary():
    # Arrange
    group = _make_group()
    cheapest = _make_snapshot(price=2500.00, origin="GRU", destination="JFK")
    route2 = _make_snapshot(price=3800.00, origin="GIG", destination="MIA")
    route3 = _make_snapshot(price=4200.00, origin="GRU", destination="MIA")
    snapshots = [cheapest, route2, route3]
    signals = _make_signals_list(1)

    # Act
    msg = compose_consolidated_email(signals, snapshots, group)

    # Assert — corpo contem resumo de rotas que nao sao a mais barata
    body = _decode_msg_body(msg)
    assert "GIG" in body
    assert "MIA" in body
    assert "R$ 3.800,00" in body
    assert "R$ 4.200,00" in body


def test_consolidated_email_silence_link():
    # Arrange
    group = _make_group(group_id=7)
    snapshots = [_make_snapshot(price=3000.00)]
    signals = _make_signals_list(1)

    # Act
    msg = compose_consolidated_email(signals, snapshots, group)

    # Assert
    body = _decode_msg_body(msg)
    assert "/api/v1/alerts/silence/" in body


def test_consolidated_email_dates_brazilian_format():
    # Arrange
    group = _make_group()
    snapshots = [
        _make_snapshot(
            departure_date=datetime.date(2026, 7, 15),
            return_date=datetime.date(2026, 7, 25),
        ),
    ]
    signals = _make_signals_list(1)

    # Act
    msg = compose_consolidated_email(signals, snapshots, group)

    # Assert — nenhuma data no formato YYYY-MM-DD, todas em dd/mm/aaaa
    body = _decode_msg_body(msg)
    assert "2026-07-15" not in body
    assert "2026-07-25" not in body
    assert "15/07/2026" in body
    assert "25/07/2026" in body


def test_consolidated_email_single_snapshot():
    # Arrange — edge case: apenas 1 snapshot
    group = _make_group(name="Single Route")
    snapshots = [_make_snapshot(price=1999.99, airline="G3")]
    signals = _make_signals_list(1)

    # Act
    msg = compose_consolidated_email(signals, snapshots, group)

    # Assert — funciona sem erro, contem dados do unico snapshot
    body = _decode_msg_body(msg)
    assert "R$ 1.999,99" in body
    assert "G3" in body
    subject = msg["Subject"]
    assert "Single Route" in subject


def test_consolidated_email_plain_text_fallback():
    # Arrange
    group = _make_group()
    snapshots = [_make_snapshot(price=2750.00)]
    signals = _make_signals_list(1)

    # Act
    msg = compose_consolidated_email(signals, snapshots, group)

    # Assert — deve ter parte text/plain com informacoes legiveis
    plain_part = None
    for part in msg.walk():
        if part.get_content_type() == "text/plain":
            plain_part = part.get_payload(decode=True).decode("utf-8")
            break

    assert plain_part is not None
    assert "GRU" in plain_part
    assert "JFK" in plain_part
    assert "2.750,00" in plain_part


# ---------------------------------------------------------------------------
# Tests — compose_consolidated_email com recipient_email (12-02)
# ---------------------------------------------------------------------------


def test_consolidated_email_recipient_email_sets_to_header():
    """compose_consolidated_email com recipient_email seta msg['To'] para o email informado."""
    # Arrange
    group = _make_group(name="GRU-MIA")
    snapshots = [_make_snapshot(price=3000.00)]
    signals = _make_signals_list(1)

    # Act
    msg = compose_consolidated_email(signals, snapshots, group, recipient_email="user@example.com")

    # Assert
    assert msg["To"] == "user@example.com"


def test_compose_alert_email_recipient_email_sets_to_header():
    """compose_alert_email com recipient_email seta msg['To'] para o email informado."""
    # Arrange
    group = _make_group()
    signal = _make_signal()

    # Act
    msg = compose_alert_email(signal, group, recipient_email="owner@example.com")

    # Assert
    assert msg["To"] == "owner@example.com"


# HYG-01, HYG-02 — Price Fidelity Hygiene (Phase 31.9)

def _extract_html_and_plain(msg):
    """Extrai payloads HTML e plain do MIMEMultipart de consolidated email."""
    html_body = ""
    plain_body = ""
    for part in msg.walk():
        ctype = part.get_content_type()
        if ctype == "text/html":
            html_body = part.get_payload(decode=True).decode("utf-8", errors="replace")
        elif ctype == "text/plain":
            plain_body = part.get_payload(decode=True).decode("utf-8", errors="replace")
    return html_body, plain_body


def test_consolidated_email_html_contem_rotulo_preco_referencia():
    group = _make_group(name="GRU-MIA")
    snapshots = [_make_snapshot(price=3200.00)]
    signals = _make_signals_list(1)

    msg = compose_consolidated_email(signals, snapshots, group)
    html, _ = _extract_html_and_plain(msg)

    assert "Preco de referencia Google Flights" in html


def test_consolidated_email_html_contem_disclaimer():
    group = _make_group(name="GRU-MIA")
    snapshots = [_make_snapshot(price=3200.00)]
    signals = _make_signals_list(1)

    msg = compose_consolidated_email(signals, snapshots, group)
    html, _ = _extract_html_and_plain(msg)

    assert "Pode divergir ate 5% do valor final" in html
    assert "bagagem e taxas nao incluidas" in html


def test_consolidated_email_plain_contem_rotulo_preco_referencia():
    group = _make_group(name="GRU-MIA")
    snapshots = [_make_snapshot(price=3200.00)]
    signals = _make_signals_list(1)

    msg = compose_consolidated_email(signals, snapshots, group)
    _, plain = _extract_html_and_plain(msg)

    assert "Preco de referencia Google Flights" in plain


def test_consolidated_email_plain_contem_disclaimer():
    group = _make_group(name="GRU-MIA")
    snapshots = [_make_snapshot(price=3200.00)]
    signals = _make_signals_list(1)

    msg = compose_consolidated_email(signals, snapshots, group)
    _, plain = _extract_html_and_plain(msg)

    assert "Pode divergir ate 5% do valor final" in plain
