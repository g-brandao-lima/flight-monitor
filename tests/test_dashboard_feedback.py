import datetime

from app.models import RouteGroup


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


# --- Flash message redirect tests ---


def test_create_group_redirects_with_msg(client, db):
    """POST /groups/create com dados validos retorna 303 com ?msg=grupo_criado."""
    response = client.post("/groups/create", data={
        "name": "Flash Test",
        "origins": "GRU",
        "destinations": "LIS",
        "duration_days": "10",
        "travel_start": "2026-05-01",
        "travel_end": "2026-05-31",
        "target_price": "",
    }, follow_redirects=False)

    assert response.status_code == 303
    assert "?msg=grupo_criado" in response.headers["location"]


def test_edit_group_redirects_with_msg(client, db):
    """POST /groups/{id}/edit retorna 303 com ?msg=grupo_atualizado."""
    group = _make_group(db)

    response = client.post(f"/groups/{group.id}/edit", data={
        "name": "Updated",
        "origins": "GRU",
        "destinations": "CDG",
        "duration_days": "14",
        "travel_start": "2026-06-01",
        "travel_end": "2026-06-30",
        "target_price": "",
    }, follow_redirects=False)

    assert response.status_code == 303
    assert "?msg=grupo_atualizado" in response.headers["location"]


def test_toggle_group_redirects_with_msg(client, db):
    """POST /groups/{id}/toggle retorna 303 com ?msg=grupo_ no Location."""
    group = _make_group(db, is_active=True)

    response = client.post(f"/groups/{group.id}/toggle", follow_redirects=False)

    assert response.status_code == 303
    assert "?msg=grupo_" in response.headers["location"]


def test_dashboard_shows_flash_message(client):
    """GET /?msg=grupo_criado retorna HTML contendo 'Grupo criado com sucesso!'."""
    response = client.get("/?msg=grupo_criado")

    assert response.status_code == 200
    assert "Grupo criado com sucesso!" in response.text


def test_dashboard_no_flash_without_param(client):
    """GET / sem param nao contem div de flash message."""
    response = client.get("/")

    assert '<div class="flash-message"' not in response.text
