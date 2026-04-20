"""Metricas agregadas para o painel admin (/admin/stats).

Fornece visao de quota SerpAPI, distribuicao de fontes, cache hit rate e
informacoes operacionais que ajudam o dono a entender a saude do sistema.
"""
import calendar
import datetime
from collections import Counter
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.models import FlightSnapshot
from app.services import flight_cache
from app.services.quota_service import (
    MONTHLY_QUOTA,
    get_current_year_month,
    get_monthly_usage,
    get_remaining_quota,
)

if TYPE_CHECKING:
    pass


def get_quota_stats(db: Session) -> dict:
    """Retorna estatisticas da quota SerpAPI mensal.

    Inclui data exata do proximo reset (primeiro dia do mes UTC seguinte).
    """
    used = get_monthly_usage(db)
    remaining = get_remaining_quota(db)
    now = datetime.datetime.utcnow()
    _, last_day = calendar.monthrange(now.year, now.month)
    next_reset = datetime.datetime(now.year, now.month, last_day, 23, 59, 59) + datetime.timedelta(seconds=1)
    days_to_reset = (next_reset.date() - now.date()).days
    pct_used = (used / MONTHLY_QUOTA * 100) if MONTHLY_QUOTA else 0.0
    return {
        "used": used,
        "limit": MONTHLY_QUOTA,
        "remaining": remaining,
        "pct_used": round(pct_used, 1),
        "year_month": get_current_year_month(),
        "next_reset_date": next_reset.date(),
        "days_to_reset": days_to_reset,
        "exhausted": remaining <= 0,
    }


def get_source_distribution(db: Session, days: int = 7) -> dict:
    """Retorna distribuicao de fontes dos snapshots coletados nos ultimos N dias.

    Chave source, valor = quantidade de snapshots. Inclui "unknown" para
    snapshots sem source preenchido (legado pre Phase 17.1).
    """
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    rows = (
        db.query(FlightSnapshot.source)
        .filter(FlightSnapshot.collected_at >= cutoff)
        .all()
    )
    counter: Counter = Counter()
    for (source,) in rows:
        key = source or "unknown"
        counter[key] += 1
    total = sum(counter.values())
    breakdown = []
    for source, count in counter.most_common():
        label = _source_label(source)
        pct = (count / total * 100) if total else 0
        breakdown.append({
            "source": source,
            "label": label,
            "count": count,
            "pct": round(pct, 1),
        })
    return {
        "total": total,
        "days": days,
        "breakdown": breakdown,
    }


def get_cache_info() -> dict:
    """Retorna estado atual do cache in-memory de search_flights."""
    return {
        "entries": flight_cache.size(),
        "ttl_minutes": 30,
    }


def _source_label(source: str) -> str:
    labels = {
        "serpapi": "Google Flights (API oficial)",
        "fast_flights": "Google Flights (fallback)",
        "kiwi": "Kiwi.com",
        "unknown": "Legado (sem fonte registrada)",
    }
    return labels.get(source, source)
