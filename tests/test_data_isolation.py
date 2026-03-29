"""Tests for data isolation between users.

Each user must only see their own route groups.
No cross-user data leakage in any route.
"""
import datetime

from app.models import RouteGroup, User
from app.services.dashboard_service import get_groups_with_summary


def _make_group(db, user_id: int, name: str = "Test Group") -> RouteGroup:
    """Helper to create a RouteGroup with a specific user_id."""
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


def test_user_a_cannot_see_user_b_groups_in_query(db, test_user, second_user):
    """RouteGroup created by user A must not appear in query filtered by user B."""
    _make_group(db, user_id=test_user.id, name="User A Group")

    groups_b = get_groups_with_summary(db, user_id=second_user.id)
    group_names = [g["group"].name for g in groups_b]
    assert "User A Group" not in group_names


def test_each_user_sees_only_own_groups(db, test_user, second_user):
    """Each user sees only their own groups via get_groups_with_summary."""
    _make_group(db, user_id=test_user.id, name="A Group")
    _make_group(db, user_id=second_user.id, name="B Group")

    groups_a = get_groups_with_summary(db, user_id=test_user.id)
    groups_b = get_groups_with_summary(db, user_id=second_user.id)

    names_a = [g["group"].name for g in groups_a]
    names_b = [g["group"].name for g in groups_b]

    assert names_a == ["A Group"]
    assert names_b == ["B Group"]


def test_dashboard_index_shows_only_user_groups(client, db, test_user, second_user):
    """Dashboard index for authenticated user shows only their groups."""
    _make_group(db, user_id=test_user.id, name="My Group")
    _make_group(db, user_id=second_user.id, name="Not My Group")

    response = client.get("/")
    assert response.status_code == 200
    assert "My Group" in response.text
    assert "Not My Group" not in response.text


def test_dashboard_detail_rejects_other_user_group(client, db, test_user, second_user):
    """Accessing detail page of another user's group returns 404."""
    other_group = _make_group(db, user_id=second_user.id, name="Other Group")

    response = client.get(f"/groups/{other_group.id}")
    assert response.status_code == 404


def test_toggle_other_user_group_returns_404(client, db, test_user, second_user):
    """Toggling another user's group returns 404."""
    other_group = _make_group(db, user_id=second_user.id, name="Other Toggle")

    response = client.post(f"/groups/{other_group.id}/toggle")
    assert response.status_code == 404


def test_create_group_assigns_current_user_id(client, db, test_user):
    """Creating a group via form assigns the logged-in user's id."""
    response = client.post(
        "/groups/create",
        data={
            "name": "New Group",
            "origins": "GRU",
            "destinations": "LIS",
            "duration_days": "7",
            "travel_start": "2026-06-01",
            "travel_end": "2026-06-30",
            "mode": "normal",
            "passengers": "1",
            "max_stops": "",
            "target_price": "",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    group = db.query(RouteGroup).filter(RouteGroup.name == "New Group").first()
    assert group is not None
    assert group.user_id == test_user.id
