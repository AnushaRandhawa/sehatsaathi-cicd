from fastapi.testclient import TestClient

from main import VERSION, app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_version_endpoint():
    r = client.get("/version")
    assert r.status_code == 200
    assert r.json()["version"] == VERSION


def test_home_page_shows_version():
    r = client.get("/")
    assert r.status_code == 200
    assert VERSION in r.text


def test_correlation_id_is_returned():
    r = client.get("/health", headers={"X-Correlation-ID": "abc-123"})
    assert r.headers["X-Correlation-ID"] == "abc-123"


def test_register_rejects_invalid_body():
    r = client.post("/patients", json={"name": "Ali"})
    assert r.status_code == 422
