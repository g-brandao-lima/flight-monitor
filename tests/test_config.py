from app.config import Settings


def test_settings_loads_defaults():
    """INFRA-02: Settings sem .env usa defaults validos."""
    # Arrange / Act
    s = Settings(_env_file=None)

    # Assert
    assert "sqlite" in s.database_url


def test_settings_has_all_fields():
    """INFRA-02: Settings possui todos os campos necessarios."""
    # Arrange / Act
    s = Settings(_env_file=None)

    # Assert
    assert hasattr(s, "amadeus_client_id")
    assert hasattr(s, "amadeus_client_secret")
    assert hasattr(s, "telegram_bot_token")
    assert hasattr(s, "telegram_chat_id")
