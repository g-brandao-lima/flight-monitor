"""Tests for data isolation in REST API /api/v1/route-groups/.

Covers gap in Phase 12 Data Isolation which only protected Dashboard routes,
leaving REST API endpoints vulnerable to cross-user data access.
"""
import datetime

from app.models import RouteGroup


def _make_group(db, user_id: int, name: str = "Group") -> RouteGroup:
    group = RouteGroup(
        user_id=user_id,
        name=name,
        origins=["GRU"],
        destinations=["LIS"],
        duration_days=7,
        travel_start=datetime.date(2026, 6, 1),
        travel_end=datetime.date(2026, 6, 30),
        is_active=True,
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


def test_list_route_groups_isolates_by_user(client, db, test_user, second_user):
    """GET /api/v1/route-groups/ retorna apenas grupos do usuario logado."""
    _make_group(db, user_id=test_user.id, name="Mine")
    _make_group(db, user_id=second_user.id, name="NotMine")

    response = client.get("/api/v1/route-groups/")
    assert response.status_code == 200
    names = [g["name"] for g in response.json()]
    assert "Mine" in names
    assert "NotMine" not in names


def test_get_other_user_group_returns_404(client, db, test_user, second_user):
    """GET /api/v1/route-groups/{id} de grupo de outro usuario retorna 404."""
    other = _make_group(db, user_id=second_user.id, name="Other")

    response = client.get(f"/api/v1/route-groups/{other.id}")
    assert response.status_code == 404


def test_patch_other_user_group_returns_404(client, db, test_user, second_user):
    """PATCH /api/v1/route-groups/{id} de grupo de outro usuario retorna 404."""
    other = _make_group(db, user_id=second_user.id, name="Other")

    response = client.patch(
        f"/api/v1/route-groups/{other.id}",
        json={"name": "Hacked"},
    )
    assert response.status_code == 404

    db.refresh(other)
    assert other.name == "Other"


def test_delete_other_user_group_returns_404(client, db, test_user, second_user):
    """DELETE /api/v1/route-groups/{id} de grupo de outro usuario retorna 404."""
    other = _make_group(db, user_id=second_user.id, name="Other")

    response = client.delete(f"/api/v1/route-groups/{other.id}")
    assert response.status_code == 404

    still_there = db.get(RouteGroup, other.id)
    assert still_there is not None
    assert still_there.name == "Other"


def test_create_assigns_current_user_id(client, db, test_user):
    """POST /api/v1/route-groups/ atribui user_id do usuario logado."""
    payload = {
        "name": "Fresh",
        "origins": ["GRU"],
        "destinations": ["LIS"],
        "duration_days": 7,
        "travel_start": "2026-07-01",
        "travel_end": "2026-07-30",
    }
    response = client.post("/api/v1/route-groups/", json=payload)
    assert response.status_code == 201

    group_id = response.json()["id"]
    group = db.get(RouteGroup, group_id)
    assert group.user_id == test_user.id


def test_get_own_group_returns_200(client, db, test_user):
    """GET grupo proprio retorna 200."""
    mine = _make_group(db, user_id=test_user.id, name="Mine")

    response = client.get(f"/api/v1/route-groups/{mine.id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Mine"


def test_patch_own_group_works(client, db, test_user):
    """PATCH grupo proprio retorna 200 e persiste."""
    mine = _make_group(db, user_id=test_user.id, name="Mine")

    response = client.patch(
        f"/api/v1/route-groups/{mine.id}",
        json={"name": "MineRenamed"},
    )
    assert response.status_code == 200

    db.refresh(mine)
    assert mine.name == "MineRenamed"


def test_delete_own_group_works(client, db, test_user):
    """DELETE grupo proprio retorna 204 e remove."""
    mine = _make_group(db, user_id=test_user.id, name="Mine")

    response = client.delete(f"/api/v1/route-groups/{mine.id}")
    assert response.status_code == 204

    assert db.get(RouteGroup, mine.id) is None


def test_unauthenticated_request_blocked(unauthenticated_client, db, test_user):
    """Requisicao sem sessao nao deve acessar a API REST."""
    _make_group(db, user_id=test_user.id, name="Mine")

    response = unauthenticated_client.get(
        "/api/v1/route-groups/", follow_redirects=False
    )
    assert response.status_code in (303, 401, 403)
