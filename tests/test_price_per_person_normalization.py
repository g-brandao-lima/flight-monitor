"""Garantia de que a busca sempre usa adults=1 (PER PERSON price).

Bug historico: ate Phase 16, adults=1 hardcoded -> price por pessoa correto.
Phase 16 passou a propagar group.passengers -> Google Flights retornou preco
TOTAL em rotas internacionais (REC-SCL etc) mas PREÇO POR PESSOA em domesticas
(CPV-CGH, REC-RAO etc). Comportamento inconsistente impossibilita normalizar
cegamente.

Solucao: sempre chamar API com adults=1. snapshot.price e sempre por pessoa.
Template multiplica por pax no display de 'total da viagem'.

Este teste previne regressao do Phase 16.
"""
from unittest.mock import MagicMock, patch


@patch("app.services.serpapi_client.GoogleSearch")
@patch("app.services.serpapi_client.settings")
def test_serpapi_always_calls_with_adults_1(mock_settings, mock_search_cls):
    """Mesmo quando caller pede adults=N, SerpAPI e chamado com adults=1."""
    from app.services.serpapi_client import SerpApiClient

    mock_settings.serpapi_api_key = "x"
    mock_instance = MagicMock()
    mock_instance.get_dict.return_value = {
        "best_flights": [{"price": 3000, "flights": [{"airline": "LATAM"}]}],
    }
    mock_search_cls.return_value = mock_instance

    client = SerpApiClient()

    client.search_flights_with_insights(
        "GRU", "LIS", "2026-09-15", "2026-09-25", adults=3
    )

    params_sent = mock_search_cls.call_args[0][0]
    assert params_sent["adults"] == 1, "Deve forcar adults=1 independente do parametro recebido"


@patch("app.services.serpapi_client.GoogleSearch")
@patch("app.services.serpapi_client.settings")
def test_serpapi_returns_price_as_is_no_division(mock_settings, mock_search_cls):
    """Price retornado nao e manipulado, vem direto da API."""
    from app.services.serpapi_client import SerpApiClient

    mock_settings.serpapi_api_key = "x"
    mock_instance = MagicMock()
    mock_instance.get_dict.return_value = {
        "best_flights": [{"price": 3000, "flights": [{"airline": "LATAM"}]}],
    }
    mock_search_cls.return_value = mock_instance

    client = SerpApiClient()
    flights, _ = client.search_flights_with_insights(
        "GRU", "LIS", "2026-09-15", "2026-09-25", adults=2
    )
    assert flights[0]["price"] == 3000, "Preco deve vir intacto da API"


# Teste de fast-flights removido na Phase 31.9 (HYG-03). SerpAPI agora
# garante adults=1 via serpapi_client; coberto por test_serpapi_client.
