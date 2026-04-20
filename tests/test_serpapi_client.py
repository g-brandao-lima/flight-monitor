from unittest.mock import patch, MagicMock
import pytest

from app.services.serpapi_client import SerpApiClient, classify_price


# --- Fixtures ---


def _make_flights_response(prices: list[int], with_insights=True) -> dict:
    """Cria resposta simulada do SerpAPI Google Flights."""
    best = []
    other = []
    for i, price in enumerate(prices):
        flight = {
            "flights": [
                {
                    "airline": "LATAM",
                    "flight_number": f"LA {1000 + i}",
                    "departure_airport": {"id": "GRU", "name": "Guarulhos"},
                    "arrival_airport": {"id": "GIG", "name": "Galeao"},
                }
            ],
            "price": price,
            "type": "Round trip",
            "airline_logo": "https://example.com/logo.png",
        }
        if i < 2:
            best.append(flight)
        else:
            other.append(flight)

    result = {
        "best_flights": best,
        "other_flights": other,
    }

    if with_insights:
        result["price_insights"] = {
            "lowest_price": min(prices),
            "typical_price_range": [400, 700],
            "price_history": [[1700000000, 500], [1700100000, 480]],
        }

    return result


# --- is_configured tests ---


@patch("app.services.serpapi_client.settings")
def test_client_not_configured_without_key(mock_settings):
    mock_settings.serpapi_api_key = ""
    client = SerpApiClient()
    assert client.is_configured is False


@patch("app.services.serpapi_client.settings")
def test_client_configured_with_key(mock_settings):
    mock_settings.serpapi_api_key = "test_key_123"
    client = SerpApiClient()
    assert client.is_configured is True


# --- search_flights_with_insights tests ---


@patch("app.services.serpapi_client.GoogleSearch")
@patch("app.services.serpapi_client.settings")
def test_search_returns_sorted_by_price(mock_settings, mock_search_cls):
    mock_settings.serpapi_api_key = "test_key"

    mock_instance = MagicMock()
    mock_instance.get_dict.return_value = _make_flights_response([500, 300, 450, 200, 350])
    mock_search_cls.return_value = mock_instance

    client = SerpApiClient()
    flights, insights = client.search_flights_with_insights("GRU", "GIG", "2026-05-01", "2026-05-08")

    assert len(flights) == 5
    prices = [f["price"] for f in flights]
    assert prices == [200, 300, 350, 450, 500]


@patch("app.services.serpapi_client.GoogleSearch")
@patch("app.services.serpapi_client.settings")
def test_search_max_results(mock_settings, mock_search_cls):
    mock_settings.serpapi_api_key = "test_key"

    mock_instance = MagicMock()
    mock_instance.get_dict.return_value = _make_flights_response(
        [500, 300, 450, 200, 350, 600, 150]
    )
    mock_search_cls.return_value = mock_instance

    client = SerpApiClient()
    flights, _ = client.search_flights_with_insights(
        "GRU", "GIG", "2026-05-01", "2026-05-08", max_results=3
    )

    assert len(flights) == 3
    prices = [f["price"] for f in flights]
    assert prices == [150, 200, 300]


@patch("app.services.serpapi_client.GoogleSearch")
@patch("app.services.serpapi_client.settings")
def test_search_passes_correct_params(mock_settings, mock_search_cls):
    mock_settings.serpapi_api_key = "my_api_key"

    mock_instance = MagicMock()
    mock_instance.get_dict.return_value = _make_flights_response([400])
    mock_search_cls.return_value = mock_instance

    client = SerpApiClient()
    client.search_flights_with_insights("GRU", "LIS", "2026-06-01", "2026-06-15")

    call_args = mock_search_cls.call_args[0][0]
    assert call_args["engine"] == "google_flights"
    assert call_args["departure_id"] == "GRU"
    assert call_args["arrival_id"] == "LIS"
    assert call_args["outbound_date"] == "2026-06-01"
    assert call_args["return_date"] == "2026-06-15"
    assert call_args["currency"] == "BRL"
    assert call_args["gl"] == "br"
    assert call_args["hl"] == "pt"
    assert call_args["api_key"] == "my_api_key"
    assert call_args["adults"] == 1


@patch("app.services.serpapi_client.GoogleSearch")
@patch("app.services.serpapi_client.settings")
def test_search_always_uses_adults_1_ignoring_caller_value(mock_settings, mock_search_cls):
    """Phase 16 revertida: adults recebido e ignorado, sempre 1.

    Google Flights retorna preco inconsistente para N adults (total em
    internacional, por pessoa em domestico). Forcamos adults=1 para
    garantir que snapshot.price e sempre por pessoa.
    """
    mock_settings.serpapi_api_key = "key"
    mock_instance = MagicMock()
    mock_instance.get_dict.return_value = _make_flights_response([400])
    mock_search_cls.return_value = mock_instance

    client = SerpApiClient()
    client.search_flights_with_insights(
        "GRU", "LIS", "2026-06-01", "2026-06-15", adults=3
    )

    call_args = mock_search_cls.call_args[0][0]
    assert call_args["adults"] == 1


@patch("app.services.serpapi_client.GoogleSearch")
@patch("app.services.serpapi_client.settings")
def test_search_empty_when_no_flights(mock_settings, mock_search_cls):
    mock_settings.serpapi_api_key = "test_key"

    mock_instance = MagicMock()
    mock_instance.get_dict.return_value = {"best_flights": [], "other_flights": []}
    mock_search_cls.return_value = mock_instance

    client = SerpApiClient()
    flights, insights = client.search_flights_with_insights("GRU", "GIG", "2026-05-01", "2026-05-08")

    assert flights == []
    assert insights is None


@patch("app.services.serpapi_client.GoogleSearch")
@patch("app.services.serpapi_client.settings")
def test_search_extracts_airline(mock_settings, mock_search_cls):
    mock_settings.serpapi_api_key = "test_key"

    response = _make_flights_response([400])
    response["best_flights"][0]["flights"][0]["airline"] = "GOL"
    mock_instance = MagicMock()
    mock_instance.get_dict.return_value = response
    mock_search_cls.return_value = mock_instance

    client = SerpApiClient()
    flights, _ = client.search_flights_with_insights("GRU", "GIG", "2026-05-01", "2026-05-08")

    assert flights[0]["airline"] == "GOL"


@patch("app.services.serpapi_client.GoogleSearch")
@patch("app.services.serpapi_client.settings")
def test_search_returns_insights_from_same_call(mock_settings, mock_search_cls):
    """Insights vem da mesma chamada API (1 call, nao 2)."""
    mock_settings.serpapi_api_key = "test_key"

    mock_instance = MagicMock()
    mock_instance.get_dict.return_value = _make_flights_response([400])
    mock_search_cls.return_value = mock_instance

    client = SerpApiClient()
    flights, insights = client.search_flights_with_insights("GRU", "GIG", "2026-05-01", "2026-05-08")

    # Apenas 1 chamada a API
    assert mock_instance.get_dict.call_count == 1

    assert insights is not None
    assert insights["lowest_price"] == 400
    assert insights["typical_price_range"] == [400, 700]


@patch("app.services.serpapi_client.GoogleSearch")
@patch("app.services.serpapi_client.settings")
def test_search_returns_none_insights_when_missing(mock_settings, mock_search_cls):
    mock_settings.serpapi_api_key = "test_key"

    mock_instance = MagicMock()
    mock_instance.get_dict.return_value = _make_flights_response([400], with_insights=False)
    mock_search_cls.return_value = mock_instance

    client = SerpApiClient()
    flights, insights = client.search_flights_with_insights("GRU", "GIG", "2026-05-01", "2026-05-08")

    assert len(flights) == 1
    assert insights is None


# --- classify_price tests ---


def test_classify_price_low():
    """Preco abaixo do range tipico = LOW."""
    result = classify_price(350.0, [400, 700])
    assert result == "LOW"


def test_classify_price_medium():
    """Preco dentro do range tipico = MEDIUM."""
    result = classify_price(500.0, [400, 700])
    assert result == "MEDIUM"


def test_classify_price_high():
    """Preco acima do range tipico = HIGH."""
    result = classify_price(800.0, [400, 700])
    assert result == "HIGH"


def test_classify_price_at_lower_bound():
    """Preco exatamente no limite inferior = MEDIUM."""
    result = classify_price(400.0, [400, 700])
    assert result == "MEDIUM"


def test_classify_price_at_upper_bound():
    """Preco exatamente no limite superior = MEDIUM."""
    result = classify_price(700.0, [400, 700])
    assert result == "MEDIUM"


def test_classify_price_no_range():
    """Sem range tipico retorna None."""
    result = classify_price(500.0, None)
    assert result is None


def test_classify_price_empty_range():
    """Range vazio retorna None."""
    result = classify_price(500.0, [])
    assert result is None
