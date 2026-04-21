def test_app_starts_and_responds(client):
    """INFRA-01: GET / retorna 200 com dashboard HTML."""
    # Arrange: client fixture provides a running test app

    # Act
    response = client.get("/")

    # Assert
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Orbita" in response.text


def test_app_has_openapi_docs(client):
    """INFRA-01: /docs endpoint retorna 200."""
    # Act
    response = client.get("/docs")

    # Assert
    assert response.status_code == 200
