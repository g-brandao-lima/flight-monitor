import datetime
from datetime import timedelta

from app.models import RouteGroup, FlightSnapshot, DetectedSignal


def _make_group(db, name="Test Group", **kwargs):
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


# --- Index page tests ---

def test_index_returns_html(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_index_shows_group_names(client, db):
    _make_group(db, name="Europa Verao")
    _make_group(db, name="Asia Inverno")

    response = client.get("/")

    assert "Europa Verao" in response.text
    assert "Asia Inverno" in response.text


def test_index_shows_cheapest_price(client, db):
    group = _make_group(db)
    _make_snapshot(db, group, price=3500.0)

    response = client.get("/")

    assert "R$ 3.500,00" in response.text


def test_index_shows_signal_badge_alta(client, db):
    group = _make_group(db)
    snap = _make_snapshot(db, group)
    _make_signal(db, group, snap, urgency="ALTA")

    response = client.get("/")

    assert "ALTA" in response.text
    assert "#f97316" in response.text


def test_index_shows_no_signal_badge(client, db):
    _make_group(db)

    response = client.get("/")

    assert "Sem sinal" in response.text


def test_index_has_viewport_meta(client):
    response = client.get("/")

    assert 'name="viewport"' in response.text


def test_index_has_responsive_css(client):
    response = client.get("/")

    assert "@media" in response.text
    assert "max-width" in response.text


def test_index_has_nav_links(client):
    response = client.get("/")

    assert 'href="/"' in response.text
    assert 'href="/groups/create"' in response.text


# --- Detail page tests ---

def test_detail_returns_html(client, db):
    group = _make_group(db)

    response = client.get(f"/groups/{group.id}")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_detail_shows_chart_data(client, db):
    group = _make_group(db)
    for i in range(3):
        collected = datetime.datetime(2026, 3, 18 + i, 10, 0)
        _make_snapshot(db, group, price=3000.0 + i * 100, collected_at=collected)

    response = client.get(f"/groups/{group.id}")

    assert "chart.js" in response.text.lower()
    assert "cdn.jsdelivr.net/npm/chart.js@4.5.1" in response.text


def test_detail_empty_group_message(client, db):
    group = _make_group(db)

    response = client.get(f"/groups/{group.id}")

    assert "Nenhum dado coletado ainda" in response.text


def test_detail_404_nonexistent(client):
    response = client.get("/groups/999")

    assert response.status_code == 404


# --- Create form tests ---

def test_create_form_page_returns_html(client):
    response = client.get("/groups/create")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "name" in response.text
    assert "origins" in response.text
    assert "destinations" in response.text
    assert 'method="POST"' in response.text.lower() or "method=\"POST\"" in response.text


def test_create_group_via_form(client, db):
    response = client.post("/groups/create", data={
        "name": "Europa Teste",
        "origins": "GRU",
        "destinations": "LIS",
        "duration_days": "10",
        "travel_start": "2026-05-01",
        "travel_end": "2026-05-31",
        "target_price": "",
    }, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"].startswith("/")
    group = db.query(RouteGroup).filter_by(name="Europa Teste").first()
    assert group is not None
    assert group.origins == ["GRU"]
    assert group.destinations == ["LIS"]


def test_create_group_uppercase_iata(client, db):
    response = client.post("/groups/create", data={
        "name": "Uppercase Test",
        "origins": "gru,cgh",
        "destinations": "lis,opo",
        "duration_days": "10",
        "travel_start": "2026-05-01",
        "travel_end": "2026-05-31",
        "target_price": "",
    }, follow_redirects=False)

    assert response.status_code == 303
    group = db.query(RouteGroup).filter_by(name="Uppercase Test").first()
    assert group is not None
    assert group.origins == ["GRU", "CGH"]
    assert group.destinations == ["LIS", "OPO"]


def test_create_group_validation_error(client, db):
    response = client.post("/groups/create", data={
        "name": "",
        "origins": "GRU",
        "destinations": "LIS",
        "duration_days": "10",
        "travel_start": "2026-05-01",
        "travel_end": "2026-05-31",
        "target_price": "",
    })

    assert response.status_code == 200
    assert "erro" in response.text.lower() or "obrigat" in response.text.lower()


def test_create_group_invalid_iata(client, db):
    response = client.post("/groups/create", data={
        "name": "IATA Invalido",
        "origins": "XX",
        "destinations": "LIS",
        "duration_days": "10",
        "travel_start": "2026-05-01",
        "travel_end": "2026-05-31",
        "target_price": "",
    })

    assert response.status_code == 200
    assert "IATA" in response.text


# --- Edit form tests ---

def test_edit_form_page_prefilled(client, db):
    group = _make_group(db, name="Editar Grupo")

    response = client.get(f"/groups/{group.id}/edit")

    assert response.status_code == 200
    assert "Editar Grupo" in response.text
    assert 'method="POST"' in response.text.lower() or "method=\"POST\"" in response.text


def test_edit_group_via_form(client, db):
    group = _make_group(db, name="Antes")

    response = client.post(f"/groups/{group.id}/edit", data={
        "name": "Depois",
        "origins": "GRU",
        "destinations": "CDG",
        "duration_days": "14",
        "travel_start": "2026-06-01",
        "travel_end": "2026-06-30",
        "target_price": "5000.00",
    }, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"].startswith("/")
    db.refresh(group)
    assert group.name == "Depois"
    assert group.destinations == ["CDG"]
    assert group.target_price == 5000.0


# --- Toggle tests ---

def test_toggle_group_active(client, db):
    group = _make_group(db, is_active=True)

    response = client.post(f"/groups/{group.id}/toggle", follow_redirects=False)

    assert response.status_code == 303
    db.refresh(group)
    assert group.is_active is False

    response = client.post(f"/groups/{group.id}/toggle", follow_redirects=False)

    assert response.status_code == 303
    db.refresh(group)
    assert group.is_active is True


def test_toggle_respects_limit(client, db):
    for i in range(10):
        _make_group(db, name=f"Active {i}", is_active=True)
    inactive = _make_group(db, name="Inactive", is_active=False)

    response = client.post(f"/groups/{inactive.id}/toggle", follow_redirects=False)

    db.refresh(inactive)
    assert inactive.is_active is False
