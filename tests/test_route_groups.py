"""Tests for Route Groups CRUD API (ROUTE-01 through ROUTE-06)."""

VALID_GROUP = {
    "name": "Europa Verao",
    "origins": ["GRU", "CGH"],
    "destinations": ["LIS", "OPO"],
    "duration_days": 14,
    "travel_start": "2026-07-01",
    "travel_end": "2026-08-31",
    "target_price": 3500.0,
}


# ---------------------------------------------------------------------------
# ROUTE-01: Criar Grupo de Rota
# ---------------------------------------------------------------------------


def test_create_route_group(client):
    """POST /api/v1/route-groups/ com body valido retorna 201 e JSON completo."""
    response = client.post("/api/v1/route-groups/", json=VALID_GROUP)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == VALID_GROUP["name"]
    assert data["origins"] == VALID_GROUP["origins"]
    assert data["destinations"] == VALID_GROUP["destinations"]
    assert data["duration_days"] == VALID_GROUP["duration_days"]
    assert data["travel_start"] == VALID_GROUP["travel_start"]
    assert data["travel_end"] == VALID_GROUP["travel_end"]
    assert data["target_price"] == VALID_GROUP["target_price"]
    assert data["is_active"] is True
    assert "id" in data


def test_create_route_group_invalid_iata(client):
    """POST com origem invalida (2 letras) retorna 422."""
    payload = {**VALID_GROUP, "origins": ["XX"]}
    response = client.post("/api/v1/route-groups/", json=payload)
    assert response.status_code == 422


def test_create_route_group_empty_origins(client):
    """POST com origins=[] retorna 422."""
    payload = {**VALID_GROUP, "origins": []}
    response = client.post("/api/v1/route-groups/", json=payload)
    assert response.status_code == 422


def test_create_route_group_invalid_duration(client):
    """POST com duration_days=0 retorna 422."""
    payload = {**VALID_GROUP, "duration_days": 0}
    response = client.post("/api/v1/route-groups/", json=payload)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# ROUTE-02: Preco-alvo opcional
# ---------------------------------------------------------------------------


def test_create_with_target_price(client):
    """POST com target_price=1500.0 retorna 201 e campo presente."""
    payload = {**VALID_GROUP, "target_price": 1500.0}
    response = client.post("/api/v1/route-groups/", json=payload)
    assert response.status_code == 201
    assert response.json()["target_price"] == 1500.0


def test_create_without_target_price(client):
    """POST sem target_price retorna 201 e target_price=null."""
    payload = {k: v for k, v in VALID_GROUP.items() if k != "target_price"}
    response = client.post("/api/v1/route-groups/", json=payload)
    assert response.status_code == 201
    assert response.json()["target_price"] is None


# ---------------------------------------------------------------------------
# ROUTE-03: Ativar/desativar
# ---------------------------------------------------------------------------


def test_deactivate_route_group(client):
    """PATCH /{id} com is_active=false retorna 200 e is_active=false."""
    create = client.post("/api/v1/route-groups/", json=VALID_GROUP)
    group_id = create.json()["id"]

    response = client.patch(
        f"/api/v1/route-groups/{group_id}", json={"is_active": False}
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_activate_route_group(client):
    """Criar grupo, desativar, e reativar via PATCH com is_active=true."""
    create = client.post("/api/v1/route-groups/", json=VALID_GROUP)
    group_id = create.json()["id"]

    # Desativar
    client.patch(f"/api/v1/route-groups/{group_id}", json={"is_active": False})

    # Reativar
    response = client.patch(
        f"/api/v1/route-groups/{group_id}", json={"is_active": True}
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is True


def test_deactivate_does_not_delete(client):
    """Apos desativar, GET /{id} retorna 200 (grupo ainda existe)."""
    create = client.post("/api/v1/route-groups/", json=VALID_GROUP)
    group_id = create.json()["id"]

    client.patch(f"/api/v1/route-groups/{group_id}", json={"is_active": False})

    response = client.get(f"/api/v1/route-groups/{group_id}")
    assert response.status_code == 200
    assert response.json()["is_active"] is False


# ---------------------------------------------------------------------------
# ROUTE-04: Editar
# ---------------------------------------------------------------------------


def test_update_route_group_name(client):
    """PATCH /{id} com name atualiza apenas o nome."""
    create = client.post("/api/v1/route-groups/", json=VALID_GROUP)
    group_id = create.json()["id"]

    response = client.patch(
        f"/api/v1/route-groups/{group_id}", json={"name": "novo nome"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "novo nome"


def test_update_route_group_origins(client):
    """PATCH /{id} com origins atualiza apenas origens."""
    create = client.post("/api/v1/route-groups/", json=VALID_GROUP)
    group_id = create.json()["id"]

    response = client.patch(
        f"/api/v1/route-groups/{group_id}", json={"origins": ["GIG"]}
    )
    assert response.status_code == 200
    assert response.json()["origins"] == ["GIG"]


def test_update_nonexistent_group(client):
    """PATCH /999 retorna 404."""
    response = client.patch("/api/v1/route-groups/999", json={"name": "x"})
    assert response.status_code == 404


def test_update_partial_fields(client):
    """PATCH com apenas um campo nao altera os demais."""
    create = client.post("/api/v1/route-groups/", json=VALID_GROUP)
    group_id = create.json()["id"]
    original = create.json()

    client.patch(f"/api/v1/route-groups/{group_id}", json={"name": "Alterado"})

    response = client.get(f"/api/v1/route-groups/{group_id}")
    updated = response.json()
    assert updated["name"] == "Alterado"
    assert updated["origins"] == original["origins"]
    assert updated["destinations"] == original["destinations"]
    assert updated["duration_days"] == original["duration_days"]
    assert updated["target_price"] == original["target_price"]


# ---------------------------------------------------------------------------
# ROUTE-05: Deletar
# ---------------------------------------------------------------------------


def test_delete_route_group(client):
    """DELETE /{id} retorna 204."""
    create = client.post("/api/v1/route-groups/", json=VALID_GROUP)
    group_id = create.json()["id"]

    response = client.delete(f"/api/v1/route-groups/{group_id}")
    assert response.status_code == 204


def test_delete_nonexistent_group(client):
    """DELETE /999 retorna 404."""
    response = client.delete("/api/v1/route-groups/999")
    assert response.status_code == 404


def test_get_after_delete(client):
    """Apos DELETE, GET /{id} retorna 404."""
    create = client.post("/api/v1/route-groups/", json=VALID_GROUP)
    group_id = create.json()["id"]

    client.delete(f"/api/v1/route-groups/{group_id}")

    response = client.get(f"/api/v1/route-groups/{group_id}")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# ROUTE-06: Limite 10 ativos
# ---------------------------------------------------------------------------


def test_max_active_groups_limit(client):
    """Criar 10 grupos ativos, tentar criar 11o retorna 409."""
    for i in range(10):
        payload = {**VALID_GROUP, "name": f"Group {i}"}
        resp = client.post("/api/v1/route-groups/", json=payload)
        assert resp.status_code == 201

    payload = {**VALID_GROUP, "name": "Group 11"}
    response = client.post("/api/v1/route-groups/", json=payload)
    assert response.status_code == 409


def test_max_active_groups_allows_after_deactivate(client):
    """Criar 10 ativos, desativar 1, criar outro (volta a 10 ativos) deve funcionar."""
    ids = []
    for i in range(10):
        payload = {**VALID_GROUP, "name": f"Group {i}"}
        resp = client.post("/api/v1/route-groups/", json=payload)
        assert resp.status_code == 201
        ids.append(resp.json()["id"])

    # Desativar um grupo (agora sao 9 ativos)
    client.patch(f"/api/v1/route-groups/{ids[0]}", json={"is_active": False})

    # Criar outro (agora sao 10 ativos novamente)
    payload = {**VALID_GROUP, "name": "Group Replacement"}
    response = client.post("/api/v1/route-groups/", json=payload)
    assert response.status_code == 201


def test_activate_exceeds_limit(client):
    """Ter 10 ativos, tentar ativar um inativo retorna 409."""
    ids = []
    for i in range(10):
        payload = {**VALID_GROUP, "name": f"Group {i}"}
        resp = client.post("/api/v1/route-groups/", json=payload)
        assert resp.status_code == 201
        ids.append(resp.json()["id"])

    # Criar 11o e desativar logo em seguida (total: 10 ativos + 1 inativo)
    # Primeiro desativar um para abrir espaco
    client.patch(f"/api/v1/route-groups/{ids[0]}", json={"is_active": False})
    payload = {**VALID_GROUP, "name": "Extra Group"}
    extra = client.post("/api/v1/route-groups/", json=payload)
    assert extra.status_code == 201
    # Agora temos 10 ativos + ids[0] inativo

    # Tentar reativar ids[0] deve falhar (ja sao 10 ativos)
    response = client.patch(
        f"/api/v1/route-groups/{ids[0]}", json={"is_active": True}
    )
    assert response.status_code == 409


# ---------------------------------------------------------------------------
# Extras: List / Get by ID / Get nonexistent
# ---------------------------------------------------------------------------


def test_list_route_groups(client):
    """GET /api/v1/route-groups/ retorna lista."""
    client.post("/api/v1/route-groups/", json=VALID_GROUP)
    client.post("/api/v1/route-groups/", json={**VALID_GROUP, "name": "Outro"})

    response = client.get("/api/v1/route-groups/")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_route_group_by_id(client):
    """GET /api/v1/route-groups/{id} retorna grupo."""
    create = client.post("/api/v1/route-groups/", json=VALID_GROUP)
    group_id = create.json()["id"]

    response = client.get(f"/api/v1/route-groups/{group_id}")
    assert response.status_code == 200
    assert response.json()["id"] == group_id
    assert response.json()["name"] == VALID_GROUP["name"]


def test_get_nonexistent_group(client):
    """GET /api/v1/route-groups/999 retorna 404."""
    response = client.get("/api/v1/route-groups/999")
    assert response.status_code == 404
