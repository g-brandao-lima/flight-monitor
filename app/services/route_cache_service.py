"""Servico de cache persistente de precos (Travelpayouts -> route_cache).

Responsavel por: (a) polling periodico alimentando route_cache via
TravelpayoutsClient; (b) lookup usado por search_flights_ex antes de SerpAPI.
"""
import datetime
import logging
from typing import Iterable

from sqlalchemy.orm import Session

from app.models import RouteCache
from app.services.travelpayouts_client import TravelpayoutsClient

logger = logging.getLogger(__name__)

DEFAULT_TTL_HOURS = 6


def get_cached_price(
    db: Session,
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str | None,
    ttl_hours: int = DEFAULT_TTL_HOURS,
) -> dict | None:
    """Retorna o menor preco cacheado dentro do TTL, ou None."""
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=ttl_hours)
    dep = datetime.date.fromisoformat(departure_date)
    ret = datetime.date.fromisoformat(return_date) if return_date else None

    q = (
        db.query(RouteCache)
        .filter(
            RouteCache.origin == origin,
            RouteCache.destination == destination,
            RouteCache.departure_date == dep,
            RouteCache.cached_at >= cutoff,
        )
        .order_by(RouteCache.min_price.asc())
    )
    if ret is not None:
        q = q.filter(RouteCache.return_date == ret)

    row = q.first()
    if row is None:
        return None
    return {
        "min_price": row.min_price,
        "currency": row.currency,
        "cached_at": row.cached_at,
        "source": "travelpayouts_cached",
    }


def _upsert(db: Session, item: dict) -> None:
    dep = datetime.date.fromisoformat(item["departure_date"])
    ret = (
        datetime.date.fromisoformat(item["return_date"])
        if item.get("return_date")
        else None
    )
    existing = (
        db.query(RouteCache)
        .filter(
            RouteCache.origin == item["origin"],
            RouteCache.destination == item["destination"],
            RouteCache.departure_date == dep,
            RouteCache.return_date == ret,
        )
        .first()
    )
    now = datetime.datetime.utcnow()
    if existing:
        existing.min_price = item["min_price"]
        existing.currency = item["currency"]
        existing.cached_at = now
        existing.source = "travelpayouts"
    else:
        db.add(RouteCache(
            origin=item["origin"],
            destination=item["destination"],
            departure_date=dep,
            return_date=ret,
            min_price=item["min_price"],
            currency=item["currency"],
            cached_at=now,
            source="travelpayouts",
        ))


def refresh_top_routes(
    db: Session,
    client: TravelpayoutsClient,
    routes: Iterable[tuple[str, str]],
    months: Iterable[str],
    currency: str = "BRL",
) -> dict:
    """Para cada (origin, destination) x mes, chama fetch_calendar e faz upsert."""
    if not client.is_configured:
        logger.warning("Travelpayouts client not configured, skipping refresh")
        return {"skipped": True, "reason": "client_not_configured"}

    from app.services.admin_stats_service import increment_travelpayouts_usage

    total_calls = 0
    total_upserts = 0
    for origin, destination in routes:
        for month in months:
            items = client.fetch_calendar(origin, destination, month, currency=currency)
            total_calls += 1
            try:
                increment_travelpayouts_usage(db)
            except Exception as e:
                logger.warning("travelpayouts usage increment failed: %s", e)
            for item in items:
                _upsert(db, item)
                total_upserts += 1
    db.commit()
    logger.info(
        "travelpayouts_refresh done: %d calls, %d upserts", total_calls, total_upserts
    )
    return {"skipped": False, "calls": total_calls, "upserts": total_upserts}


TOP_BR_ROUTES: list[tuple[str, str]] = [
    ("GRU", "GIG"), ("GIG", "GRU"), ("GRU", "SSA"), ("GRU", "REC"), ("GRU", "FOR"),
    ("CGH", "SDU"), ("GRU", "BSB"), ("GRU", "POA"), ("GRU", "CWB"), ("GRU", "CNF"),
    ("GRU", "MAO"), ("GIG", "SSA"), ("BSB", "GRU"), ("REC", "GRU"), ("FOR", "GRU"),
    ("GRU", "LIS"), ("GRU", "MAD"), ("GRU", "MIA"), ("GRU", "JFK"), ("GRU", "SCL"),
    ("GRU", "EZE"), ("GIG", "SCL"), ("BSB", "SCL"), ("GIG", "EZE"),
    ("GRU", "LIM"), ("GRU", "BOG"), ("GRU", "MEX"),
    ("GRU", "LHR"), ("GRU", "CDG"), ("GRU", "FCO"), ("GRU", "BCN"),
    ("GRU", "FRA"), ("GIG", "LIS"), ("GIG", "MIA"),
]


def _next_n_months(n: int) -> list[str]:
    today = datetime.date.today()
    out = []
    y, m = today.year, today.month
    for _ in range(n):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out
