from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.models import (
    FlightSnapshot,
    BookingClassSnapshot,
    DetectedSignal,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CLOSING_CLASSES = {"K", "Q"}
CLOSING_THRESHOLD_FROM = 3
CLOSING_THRESHOLD_TO = 1

BRAZILIAN_AIRPORTS = {
    "GRU", "CGH", "VCP",
    "GIG", "SDU",
    "BSB",
    "CNF", "PLU",
    "SSA",
    "REC",
    "FOR",
    "POA",
    "CWB",
    "FLN",
    "BEL",
    "MAO",
    "NAT",
    "MCZ",
    "VIX",
    "CGB",
    "GYN",
    "SLZ",
    "THE",
    "AJU",
    "JPA",
    "PMW",
    "IGU",
}

DOMESTIC_WINDOW = (21, 90)
INTERNATIONAL_WINDOW = (30, 120)

MIN_SNAPSHOTS_FOR_PRICE = 3


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def detect_signals(
    db: Session, snapshot: FlightSnapshot
) -> list[DetectedSignal]:
    """Orquestra deteccao de todos os tipos de sinal para um snapshot."""
    previous = _get_previous_snapshot(db, snapshot)

    candidates: list[DetectedSignal] = []

    balde_fechando = _check_balde_fechando(snapshot, previous)
    if balde_fechando:
        candidates.append(balde_fechando)

    balde_reaberto = _check_balde_reaberto(snapshot, previous)
    if balde_reaberto:
        candidates.append(balde_reaberto)

    preco = _check_preco_abaixo_historico(db, snapshot)
    if preco:
        candidates.append(preco)

    janela = _check_janela_otima(snapshot)
    if janela:
        candidates.append(janela)

    new_signals: list[DetectedSignal] = []
    reference_time = snapshot.collected_at or datetime.utcnow()
    for signal in candidates:
        if not _is_duplicate(db, signal, reference_time):
            db.add(signal)
            new_signals.append(signal)

    if new_signals:
        db.commit()

    return new_signals


# ---------------------------------------------------------------------------
# Previous snapshot query
# ---------------------------------------------------------------------------


def _get_previous_snapshot(
    db: Session, current: FlightSnapshot
) -> FlightSnapshot | None:
    """Busca o snapshot imediatamente anterior para a mesma rota."""
    return (
        db.query(FlightSnapshot)
        .filter(
            FlightSnapshot.route_group_id == current.route_group_id,
            FlightSnapshot.origin == current.origin,
            FlightSnapshot.destination == current.destination,
            FlightSnapshot.departure_date == current.departure_date,
            FlightSnapshot.return_date == current.return_date,
            FlightSnapshot.id != current.id,
            FlightSnapshot.collected_at < current.collected_at,
        )
        .order_by(FlightSnapshot.collected_at.desc())
        .first()
    )


# ---------------------------------------------------------------------------
# Booking class helpers
# ---------------------------------------------------------------------------


def _booking_classes_to_dict(
    booking_classes: list[BookingClassSnapshot],
) -> dict[str, int]:
    """Converte lista de BookingClassSnapshot em dict {class_code: min_seats}.
    Usa minimo entre OUTBOUND e INBOUND como gargalo."""
    result: dict[str, int] = {}
    for bc in booking_classes:
        code = bc.class_code
        if code not in result:
            result[code] = bc.seats_available
        else:
            result[code] = min(result[code], bc.seats_available)
    return result


def _is_domestic(origin: str, destination: str) -> bool:
    return origin in BRAZILIAN_AIRPORTS and destination in BRAZILIAN_AIRPORTS


# ---------------------------------------------------------------------------
# Detectors (pure functions, no db.add)
# ---------------------------------------------------------------------------


def _check_balde_fechando(
    current: FlightSnapshot, previous: FlightSnapshot | None
) -> DetectedSignal | None:
    if previous is None:
        return None

    prev_classes = _booking_classes_to_dict(previous.booking_classes)
    curr_classes = _booking_classes_to_dict(current.booking_classes)

    for class_code in CLOSING_CLASSES:
        prev_seats = prev_classes.get(class_code, 0)
        curr_seats = curr_classes.get(class_code, 0)

        if prev_seats >= CLOSING_THRESHOLD_FROM and curr_seats <= CLOSING_THRESHOLD_TO:
            return DetectedSignal(
                route_group_id=current.route_group_id,
                flight_snapshot_id=current.id,
                origin=current.origin,
                destination=current.destination,
                departure_date=current.departure_date,
                return_date=current.return_date,
                signal_type="BALDE_FECHANDO",
                urgency="ALTA",
                details=f"Classe {class_code}: {prev_seats} -> {curr_seats} assentos",
                price_at_detection=current.price,
            )
    return None


def _check_balde_reaberto(
    current: FlightSnapshot, previous: FlightSnapshot | None
) -> DetectedSignal | None:
    if previous is None:
        return None

    prev_classes = _booking_classes_to_dict(previous.booking_classes)
    curr_classes = _booking_classes_to_dict(current.booking_classes)

    reopened = []
    for class_code, curr_seats in curr_classes.items():
        prev_seats = prev_classes.get(class_code, 0)
        if prev_seats == 0 and curr_seats > 0:
            reopened.append(f"{class_code}: 0 -> {curr_seats}")

    if reopened:
        return DetectedSignal(
            route_group_id=current.route_group_id,
            flight_snapshot_id=current.id,
            origin=current.origin,
            destination=current.destination,
            departure_date=current.departure_date,
            return_date=current.return_date,
            signal_type="BALDE_REABERTO",
            urgency="MAXIMA",
            details=f"Classes reabriram: {', '.join(reopened)}",
            price_at_detection=current.price,
        )
    return None


def _check_preco_abaixo_historico(
    db: Session, snapshot: FlightSnapshot
) -> DetectedSignal | None:
    if snapshot.price_classification != "LOW":
        return None

    avg_price, count = _get_avg_price_last_n(db, snapshot, n=14)

    if count < MIN_SNAPSHOTS_FOR_PRICE:
        return None

    if avg_price is not None and snapshot.price < avg_price:
        return DetectedSignal(
            route_group_id=snapshot.route_group_id,
            flight_snapshot_id=snapshot.id,
            origin=snapshot.origin,
            destination=snapshot.destination,
            departure_date=snapshot.departure_date,
            return_date=snapshot.return_date,
            signal_type="PRECO_ABAIXO_HISTORICO",
            urgency="MEDIA",
            details=(
                f"Preco {snapshot.price:.2f} abaixo da media "
                f"{avg_price:.2f} dos ultimos {count} snapshots"
            ),
            price_at_detection=snapshot.price,
        )
    return None


def _check_janela_otima(
    snapshot: FlightSnapshot,
) -> DetectedSignal | None:
    today = date.today()
    days_until = (snapshot.departure_date - today).days

    if days_until <= 0:
        return None

    domestic = _is_domestic(snapshot.origin, snapshot.destination)
    window = DOMESTIC_WINDOW if domestic else INTERNATIONAL_WINDOW

    if window[0] <= days_until <= window[1]:
        route_type = "domestico" if domestic else "internacional"
        return DetectedSignal(
            route_group_id=snapshot.route_group_id,
            flight_snapshot_id=snapshot.id,
            origin=snapshot.origin,
            destination=snapshot.destination,
            departure_date=snapshot.departure_date,
            return_date=snapshot.return_date,
            signal_type="JANELA_OTIMA",
            urgency="MEDIA",
            details=(
                f"Voo {route_type} em {days_until} dias "
                f"(janela ideal: {window[0]}-{window[1]} dias)"
            ),
            price_at_detection=snapshot.price,
        )
    return None


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


def _is_duplicate(
    db: Session, signal: DetectedSignal, reference_time: datetime
) -> bool:
    """Verifica se sinal identico foi emitido nas ultimas 12 horas."""
    cutoff = reference_time - timedelta(hours=12)
    existing = (
        db.query(DetectedSignal)
        .filter(
            DetectedSignal.route_group_id == signal.route_group_id,
            DetectedSignal.origin == signal.origin,
            DetectedSignal.destination == signal.destination,
            DetectedSignal.departure_date == signal.departure_date,
            DetectedSignal.return_date == signal.return_date,
            DetectedSignal.signal_type == signal.signal_type,
            DetectedSignal.detected_at >= cutoff,
        )
        .first()
    )
    return existing is not None


# ---------------------------------------------------------------------------
# Price average helper
# ---------------------------------------------------------------------------


def _get_avg_price_last_n(
    db: Session, snapshot: FlightSnapshot, n: int = 14
) -> tuple[float | None, int]:
    """Retorna (media_de_preco, contagem) dos ultimos N snapshots da mesma rota."""
    subquery = (
        select(FlightSnapshot.price)
        .where(
            FlightSnapshot.route_group_id == snapshot.route_group_id,
            FlightSnapshot.origin == snapshot.origin,
            FlightSnapshot.destination == snapshot.destination,
            FlightSnapshot.departure_date == snapshot.departure_date,
            FlightSnapshot.return_date == snapshot.return_date,
            FlightSnapshot.id != snapshot.id,
            FlightSnapshot.collected_at < snapshot.collected_at,
        )
        .order_by(FlightSnapshot.collected_at.desc())
        .limit(n)
        .subquery()
    )
    result = db.execute(
        select(sa_func.avg(subquery.c.price), sa_func.count())
    ).one()
    return result[0], result[1]
