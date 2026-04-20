"""Subject line factual do email consolidado (Phase 26)."""
import datetime
from datetime import date
from unittest.mock import MagicMock

from app.services.alert_service import _build_subject


def _make_snap(price=3000.0, origin="GRU", destination="LIS"):
    s = MagicMock()
    s.price = price
    s.origin = origin
    s.destination = destination
    s.departure_date = date(2026, 7, 10)
    s.return_date = date(2026, 7, 17)
    s.airline = "LATAM"
    s.source = "serpapi"
    return s


def _make_group(name="Europa Verao"):
    g = MagicMock()
    g.name = name
    g.passengers = 1
    return g


def test_subject_no_context_uses_fallback():
    subj = _build_subject(_make_snap(), None, _make_group())
    assert "Europa Verao" in subj
    assert "R$" in subj


def test_subject_significant_drop_highlights_percent():
    ctx = {"avg": 4000.0, "min": 3000.0, "max": 5000.0, "count": 20, "days": 90}
    subj = _build_subject(_make_snap(price=3000.0), ctx, _make_group())
    assert "caiu" in subj
    assert "25%" in subj
    assert "GRU-LIS" in subj


def test_subject_mild_drop_uses_abaixo_da_media():
    ctx = {"avg": 4000.0, "min": 3500.0, "max": 5000.0, "count": 20, "days": 90}
    subj = _build_subject(_make_snap(price=3700.0), ctx, _make_group())
    assert "abaixo da media" in subj
    assert "%" in subj


def test_subject_in_line_without_percent():
    ctx = {"avg": 4000.0, "min": 3500.0, "max": 4500.0, "count": 20, "days": 90}
    subj = _build_subject(_make_snap(price=4000.0), ctx, _make_group())
    assert "em R$" in subj
    assert "media 90d" in subj


def test_subject_significant_rise():
    ctx = {"avg": 4000.0, "min": 3500.0, "max": 5000.0, "count": 20, "days": 90}
    subj = _build_subject(_make_snap(price=4500.0), ctx, _make_group())
    assert "subiu" in subj
    assert "%" in subj


def test_subject_includes_route_code_first():
    ctx = {"avg": 4000.0, "min": 3500.0, "max": 5000.0, "count": 20, "days": 90}
    subj = _build_subject(_make_snap(origin="GIG", destination="CDG"), ctx, _make_group())
    assert subj.startswith("GIG-CDG")
