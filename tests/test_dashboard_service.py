import datetime
from datetime import timedelta

from app.models import RouteGroup, FlightSnapshot, DetectedSignal
from app.services.dashboard_service import (
    get_groups_with_summary,
    get_price_history,
    format_price_brl,
    booking_urls,
)


def test_booking_urls_decolar_uses_multipleoneway_format():
    urls = booking_urls(
        origin="REC",
        destination="RAO",
        departure_date=datetime.date(2026, 9, 15),
        return_date=datetime.date(2026, 9, 22),
        passengers=2,
    )
    assert urls["decolar"] == (
        "https://www.decolar.com/shop/flights/results/multipleoneway/"
        "REC/RAO/2026-09-15/2026-09-22/2/0/0"
        "?from=SB&di=1&isRedirectFromRoundtrip=true"
    )


def test_booking_urls_decolar_defaults_to_single_passenger():
    urls = booking_urls(
        origin="GRU",
        destination="LIS",
        departure_date=datetime.date(2026, 6, 1),
        return_date=datetime.date(2026, 6, 10),
    )
    assert "/1/0/0?from=SB&di=1" in urls["decolar"]


def test_booking_urls_google_flights_uses_hash_flt_format():
    """Hash-based #flt= preenche a busca; o formato ?q= abria a home vazia."""
    urls = booking_urls(
        origin="REC",
        destination="SCL",
        departure_date=datetime.date(2026, 7, 8),
        return_date=datetime.date(2026, 7, 15),
    )
    assert urls["google_flights"].startswith(
        "https://www.google.com/travel/flights?hl=pt-BR&curr=BRL#flt="
    )
    assert "REC.SCL.2026-07-08*SCL.REC.2026-07-15" in urls["google_flights"]


def test_booking_urls_kayak_br_com_passageiros():
    urls = booking_urls(
        origin="REC",
        destination="SCL",
        departure_date=datetime.date(2026, 7, 8),
        return_date=datetime.date(2026, 7, 15),
        passengers=2,
    )
    assert urls["kayak"] == (
        "https://www.kayak.com.br/flights/REC-SCL/2026-07-08/2026-07-15/2adults"
    )


def test_booking_urls_kayak_sem_sufixo_quando_solo():
    urls = booking_urls(
        origin="REC",
        destination="SCL",
        departure_date=datetime.date(2026, 7, 8),
        return_date=datetime.date(2026, 7, 15),
    )
    assert urls["kayak"].endswith("/2026-07-08/2026-07-15")
    assert "adults" not in urls["kayak"]


def _make_group(db, name="Test Group", group_id=None, **kwargs):
    defaults = dict(
        name=name,
        origins=["GRU"],
        destinations=["LIS"],
        duration_days=10,
        travel_start=datetime.date(2026, 5, 1),
        travel_end=datetime.date(2026, 5, 31),
        is_active=True,
    )
    defaults.update(kwargs)
    group = RouteGroup(**defaults)
    if group_id is not None:
        group.id = group_id
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


def _make_snapshot(db, group, price=3000.0, origin="GRU", destination="LIS",
                   collected_at=None, **kwargs):
    if collected_at is None:
        collected_at = datetime.datetime(2026, 3, 20, 12, 0)
    defaults = dict(
        route_group_id=group.id,
        origin=origin,
        destination=destination,
        departure_date=datetime.date(2026, 5, 10),
        return_date=datetime.date(2026, 5, 20),
        price=price,
        currency="BRL",
        airline="LA",
        collected_at=collected_at,
    )
    defaults.update(kwargs)
    snap = FlightSnapshot(**defaults)
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return snap


def _make_signal(db, group, snapshot, urgency="MEDIA", detected_at=None, **kwargs):
    if detected_at is None:
        detected_at = datetime.datetime.utcnow()
    defaults = dict(
        route_group_id=group.id,
        flight_snapshot_id=snapshot.id,
        origin=snapshot.origin,
        destination=snapshot.destination,
        departure_date=snapshot.departure_date,
        return_date=snapshot.return_date,
        signal_type="BALDE_FECHANDO",
        urgency=urgency,
        details="Test signal",
        price_at_detection=snapshot.price,
        detected_at=detected_at,
    )
    defaults.update(kwargs)
    signal = DetectedSignal(**defaults)
    db.add(signal)
    db.commit()
    db.refresh(signal)
    return signal


# --- get_groups_with_summary tests ---

def test_get_groups_with_summary_returns_all_groups(db):
    _make_group(db, name="Group A")
    _make_group(db, name="Group B")

    result = get_groups_with_summary(db)

    assert len(result) == 2
    for item in result:
        assert "group" in item
        assert "cheapest_snapshot" in item
        assert "signal" in item


def test_get_groups_with_summary_includes_cheapest_price(db):
    group = _make_group(db)
    now = datetime.datetime(2026, 3, 20, 12, 0)
    _make_snapshot(db, group, price=5000.0, collected_at=now)
    _make_snapshot(db, group, price=3000.0, collected_at=now)

    result = get_groups_with_summary(db)

    assert result[0]["cheapest_snapshot"] is not None
    assert result[0]["cheapest_snapshot"].price == 3000.0


def test_get_groups_with_summary_includes_most_urgent_signal(db):
    group = _make_group(db)
    snap = _make_snapshot(db, group)
    now = datetime.datetime.utcnow()
    _make_signal(db, group, snap, urgency="MEDIA", detected_at=now)
    _make_signal(db, group, snap, urgency="ALTA", detected_at=now)

    result = get_groups_with_summary(db)

    assert result[0]["signal"] is not None
    assert result[0]["signal"].urgency == "ALTA"


def test_get_groups_with_summary_no_snapshots(db):
    _make_group(db)

    result = get_groups_with_summary(db)

    assert result[0]["cheapest_snapshot"] is None


def test_get_groups_with_summary_no_signals(db):
    group = _make_group(db)
    _make_snapshot(db, group)

    result = get_groups_with_summary(db)

    assert result[0]["signal"] is None


def test_get_groups_with_summary_old_signal_ignored(db):
    group = _make_group(db)
    snap = _make_snapshot(db, group)
    old_time = datetime.datetime.utcnow() - timedelta(hours=13)
    _make_signal(db, group, snap, urgency="ALTA", detected_at=old_time)

    result = get_groups_with_summary(db)

    assert result[0]["signal"] is None


# --- get_price_history tests ---

def test_get_price_history_returns_labels_and_prices(db):
    group = _make_group(db)
    base = datetime.datetime.utcnow() - timedelta(days=5)
    for i in range(3):
        collected = base + timedelta(days=i)
        _make_snapshot(db, group, price=3000.0 + i * 100, collected_at=collected)

    result = get_price_history(db, group.id)

    assert len(result["labels"]) == 3
    assert len(result["prices"]) == 3
    assert result["prices"][0] == 3000.0


def test_get_price_history_filters_cheapest_route(db):
    group = _make_group(db)
    now = datetime.datetime.utcnow() - timedelta(days=1)
    # Expensive route
    _make_snapshot(db, group, price=8000.0, origin="GRU", destination="CDG",
                   collected_at=now)
    # Cheap route
    _make_snapshot(db, group, price=2500.0, origin="GRU", destination="LIS",
                   collected_at=now)

    result = get_price_history(db, group.id)

    assert "GRU" in result["route"]
    assert "LIS" in result["route"]
    assert result["prices"][0] == 2500.0


def test_get_price_history_empty_group(db):
    group = _make_group(db)

    result = get_price_history(db, group.id)

    assert result == {"labels": [], "prices": [], "route": ""}


def test_get_price_history_respects_14_day_cutoff(db):
    group = _make_group(db)
    old = datetime.datetime.utcnow() - timedelta(days=15)
    recent = datetime.datetime.utcnow() - timedelta(days=13)
    _make_snapshot(db, group, price=3000.0, collected_at=old)
    _make_snapshot(db, group, price=3500.0, collected_at=recent)

    result = get_price_history(db, group.id)

    assert len(result["prices"]) == 1
    assert result["prices"][0] == 3500.0


# --- format_price_brl tests ---

def test_format_price_brl(db):
    assert format_price_brl(3500.0) == "R$ 3.500,00"
    assert format_price_brl(123.5) == "R$ 123,50"


# --- get_dashboard_summary tests ---

from app.services.dashboard_service import get_dashboard_summary, format_date_br


def test_get_dashboard_summary_active_count(db):
    _make_group(db, name="Active 1", is_active=True)
    _make_group(db, name="Active 2", is_active=True)
    _make_group(db, name="Inactive", is_active=False)

    result = get_dashboard_summary(db)

    assert result["active_count"] == 2


def test_get_dashboard_summary_cheapest_price_none_when_no_snapshots(db):
    _make_group(db, name="Empty group")

    result = get_dashboard_summary(db)

    assert result["cheapest_price"] is None


def test_get_dashboard_summary_cheapest_price_across_groups(db):
    group_a = _make_group(db, name="Group A")
    group_b = _make_group(db, name="Group B")
    now = datetime.datetime(2026, 3, 20, 12, 0)
    _make_snapshot(db, group_a, price=5000.0, collected_at=now)
    _make_snapshot(db, group_b, price=2500.0, collected_at=now)

    result = get_dashboard_summary(db)

    assert result["cheapest_price"] == 2500.0


def test_get_dashboard_summary_has_next_polling(db):
    result = get_dashboard_summary(db)

    assert "next_polling" in result
    assert isinstance(result["next_polling"], str)


def test_format_date_br_formats_correctly():
    d = datetime.date(2026, 3, 25)
    assert format_date_br(d) == "25/03/2026"


def test_format_date_br_handles_none():
    assert format_date_br(None) == ""


# --- Filtro por origens/destinos atuais do grupo ---


def test_get_groups_with_summary_ignores_snapshots_from_removed_origin(db):
    """Apos editar grupo e remover uma origem, snapshots da origem antiga
    nao devem aparecer como cheapest_snapshot."""
    group = _make_group(db, origins=["REC", "JPA"], destinations=["CGH"])
    now = datetime.datetime(2026, 3, 20, 12, 0)
    # Snapshot antigo com REC (mais barato)
    _make_snapshot(db, group, price=800.0, origin="REC", destination="CGH",
                   collected_at=now)
    # Snapshot com JPA (mais caro)
    _make_snapshot(db, group, price=1200.0, origin="JPA", destination="CGH",
                   collected_at=now)

    # Simula edicao: usuario removeu REC, ficou so JPA
    group.origins = ["JPA"]
    db.commit()

    result = get_groups_with_summary(db)

    assert result[0]["cheapest_snapshot"] is not None
    assert result[0]["cheapest_snapshot"].origin == "JPA"
    assert result[0]["cheapest_snapshot"].price == 1200.0


def test_get_groups_with_summary_ignores_snapshots_from_removed_destination(db):
    """Apos editar grupo e remover um destino, snapshots do destino antigo
    nao devem aparecer."""
    group = _make_group(db, origins=["JPA"], destinations=["CGH", "GRU"])
    now = datetime.datetime(2026, 3, 20, 12, 0)
    _make_snapshot(db, group, price=900.0, origin="JPA", destination="GRU",
                   collected_at=now)
    _make_snapshot(db, group, price=1500.0, origin="JPA", destination="CGH",
                   collected_at=now)

    # Simula edicao: removeu GRU
    group.destinations = ["CGH"]
    db.commit()

    result = get_groups_with_summary(db)

    assert result[0]["cheapest_snapshot"].destination == "CGH"
    assert result[0]["cheapest_snapshot"].price == 1500.0


def test_get_dashboard_summary_ignores_snapshots_from_removed_origin(db):
    """Menor preco global nao deve considerar snapshots de origens removidas."""
    group = _make_group(db, origins=["REC", "JPA"], destinations=["CGH"])
    now = datetime.datetime(2026, 3, 20, 12, 0)
    _make_snapshot(db, group, price=500.0, origin="REC", destination="CGH",
                   collected_at=now)
    _make_snapshot(db, group, price=1000.0, origin="JPA", destination="CGH",
                   collected_at=now)

    group.origins = ["JPA"]
    db.commit()

    result = get_dashboard_summary(db)

    assert result["cheapest_price"] == 1000.0


# --- best_day and collection_count dialect-agnostic tests ---


def test_best_day_returns_correct_day_name(db):
    """best_day retorna o nome do dia da semana com menor media de preco
    quando ha >= 3 snapshots naquele dia."""
    group = _make_group(db)
    now = datetime.datetime(2026, 3, 20, 12, 0)
    # Sunday (2026-05-10 is a Sunday) - 3 snapshots, avg = 4000
    for i in range(3):
        _make_snapshot(db, group, price=3500.0 + i * 500,
                       departure_date=datetime.date(2026, 5, 10),
                       collected_at=now + timedelta(hours=i))
    # Monday (2026-05-11) - 3 snapshots, avg = 2000 (cheaper!)
    for i in range(3):
        _make_snapshot(db, group, price=1500.0 + i * 500,
                       departure_date=datetime.date(2026, 5, 11),
                       collected_at=now + timedelta(hours=i))

    result = get_groups_with_summary(db)

    assert result[0]["best_day"] is not None
    assert result[0]["best_day"]["name"] == "Segunda"
    assert result[0]["best_day"]["avg_price"] == 2000.0


def test_best_day_returns_none_when_less_than_3_snapshots(db):
    """best_day retorna None quando nenhum dia da semana tem >= 3 snapshots."""
    group = _make_group(db)
    now = datetime.datetime(2026, 3, 20, 12, 0)
    # Only 2 snapshots for same day
    _make_snapshot(db, group, price=3000.0,
                   departure_date=datetime.date(2026, 5, 10),
                   collected_at=now)
    _make_snapshot(db, group, price=3500.0,
                   departure_date=datetime.date(2026, 5, 10),
                   collected_at=now + timedelta(hours=1))

    result = get_groups_with_summary(db)

    assert result[0]["best_day"] is None


def test_collection_count_counts_distinct_hours(db):
    """collection_count conta horas distintas de coleta."""
    group = _make_group(db)
    # 3 snapshots in same hour = 1 collection
    base = datetime.datetime(2026, 3, 20, 12, 0)
    _make_snapshot(db, group, price=3000.0, collected_at=base)
    _make_snapshot(db, group, price=3100.0,
                   collected_at=base + timedelta(minutes=15))
    _make_snapshot(db, group, price=3200.0,
                   collected_at=base + timedelta(minutes=30))
    # 1 snapshot in different hour = 2nd collection
    _make_snapshot(db, group, price=2900.0,
                   collected_at=base + timedelta(hours=6))

    result = get_groups_with_summary(db)

    assert result[0]["collection_count"] == 2


def test_get_price_history_ignores_snapshots_from_removed_origin(db):
    """Historico de preco nao deve mostrar rota de origem removida."""
    group = _make_group(db, origins=["REC", "JPA"], destinations=["CGH"])
    now = datetime.datetime.utcnow() - timedelta(days=1)
    # REC mais barato (seria a "cheapest route" sem filtro)
    _make_snapshot(db, group, price=600.0, origin="REC", destination="CGH",
                   collected_at=now)
    _make_snapshot(db, group, price=1100.0, origin="JPA", destination="CGH",
                   collected_at=now)

    group.origins = ["JPA"]
    db.commit()

    result = get_price_history(db, group.id)

    assert "JPA" in result["route"]
    assert "REC" not in result["route"]
