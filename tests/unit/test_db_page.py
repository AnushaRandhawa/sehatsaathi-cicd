from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_db_page_shows_table_rows():
    r = client.get("/db")
    assert r.status_code == 200
    assert "<th>name</th>" in r.text
    assert "Ayesha Khan" in r.text
