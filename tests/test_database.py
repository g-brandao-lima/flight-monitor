from sqlalchemy import inspect

from tests.conftest import engine


def test_tables_created_on_startup(db):
    """INFRA-03: Tabela route_groups existe apos create_all."""
    # Arrange: db fixture calls Base.metadata.create_all

    # Act
    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    # Assert
    assert "route_groups" in table_names


def test_route_groups_table_columns(db):
    """INFRA-03: Colunas obrigatorias existem na tabela route_groups."""
    # Arrange
    inspector = inspect(engine)

    # Act
    columns = inspector.get_columns("route_groups")
    column_names = [col["name"] for col in columns]

    # Assert
    expected_columns = [
        "id", "name", "origins", "destinations",
        "duration_days", "travel_start", "travel_end",
        "target_price", "is_active",
    ]
    for col in expected_columns:
        assert col in column_names, f"Column '{col}' not found in route_groups table"
