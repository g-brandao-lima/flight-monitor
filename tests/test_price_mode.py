"""Toggle de modo de exibicao de preco (Phase 25)."""
import datetime
from datetime import date

from app.models import RouteGroup


def _make_group(db, user_id):
    rg = RouteGroup(
        user_id=user_id,
        name="G",
        origins=["GRU"],
        destinations=["LIS"],
        duration_days=7,
        travel_start=date(2026, 7, 1),
        travel_end=date(2026, 7, 31),
        is_active=True,
    )
    db.add(rg)
    db.commit()
    return rg


def test_default_mode_per_person(client, test_user, db):
    """Dashboard sem cookie mostra modo 'Por pessoa' ativo."""
    _make_group(db, test_user.id)
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 200
    html = response.text
    assert "Por pessoa" in html
    assert "Total da viagem" in html
    # O botao com value=per_person deve ter classe active no mesmo elemento
    idx = html.find('value="per_person"')
    snippet = html[idx:idx + 200]
    assert "price-mode-btn active" in snippet


def test_set_mode_total_persists_cookie(client):
    """POST /preferences/price-mode com mode=total seta cookie."""
    response = client.post(
        "/preferences/price-mode",
        data={"mode": "total"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.cookies.get("price_mode") == "total"


def test_invalid_mode_falls_back_to_per_person(client):
    """Mode invalido e normalizado."""
    response = client.post(
        "/preferences/price-mode",
        data={"mode": "hackish_value"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.cookies.get("price_mode") == "per_person"


def test_cookie_total_switches_display(client, test_user, db):
    """Com cookie price_mode=total, dashboard renderiza modo 'Total'."""
    _make_group(db, test_user.id)
    client.cookies.set("price_mode", "total")
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 200
    html = response.text
    idx = html.find('value="total"')
    snippet = html[idx:idx + 200]
    assert "price-mode-btn active" in snippet
