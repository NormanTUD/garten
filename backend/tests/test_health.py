from httpx import AsyncClient


async def test_health_endpoint(client: AsyncClient):
    response = await client.get("/api/health")

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "GartenApp"
    assert "version" in data


async def test_openapi_docs_available(client: AsyncClient):
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    assert "openapi" in response.json()


async def test_health_returns_json_content_type(client: AsyncClient):
    response = await client.get("/api/health")

    assert response.headers["content-type"] == "application/json"
