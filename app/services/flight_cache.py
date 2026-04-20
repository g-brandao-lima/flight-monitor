"""Cache in-memory para resultados de search_flights.

Evita chamadas duplicadas a APIs externas (SerpAPI, fast-flights) quando
multiplos grupos monitoram a mesma rota/data/passageiros. TTL padrao 30 min
cobre 1 ciclo de polling inteiro (2 ciclos/dia).

Nao persiste entre reinicios: aceitavel porque polling e programado e o cache
aquece naturalmente.
"""
import threading
import time
from typing import Any

_DEFAULT_TTL_SECONDS = 30 * 60

_cache: dict[tuple, tuple[float, Any]] = {}
_lock = threading.Lock()


def make_key(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str,
    max_stops: int | None,
    adults: int,
) -> tuple:
    return (origin, destination, departure_date, return_date, max_stops, adults)


def get(key: tuple, ttl_seconds: int = _DEFAULT_TTL_SECONDS) -> Any | None:
    """Retorna o valor em cache ou None se ausente/expirado."""
    now = time.monotonic()
    with _lock:
        entry = _cache.get(key)
        if entry is None:
            return None
        stored_at, value = entry
        if now - stored_at > ttl_seconds:
            _cache.pop(key, None)
            return None
        return value


def put(key: tuple, value: Any) -> None:
    """Armazena um valor no cache com timestamp atual."""
    now = time.monotonic()
    with _lock:
        _cache[key] = (now, value)


def clear() -> None:
    """Limpa todo o cache. Uso primario em testes."""
    with _lock:
        _cache.clear()


def size() -> int:
    with _lock:
        return len(_cache)
