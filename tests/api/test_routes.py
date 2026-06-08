from fastapi.testclient import TestClient
from tracking_agent.api.app import create_app


def test_track_endpoint():
    client = TestClient(create_app())
    resp = client.post("/track", json={"shipments": [
        {"id": "a", "number": "080-38652331"},
        {"id": "b", "number": "hello"}]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["total"] == 2
    assert data["results"][1]["errors"][0]["code"] == "INVALID_FORMAT"


def test_index_returns_html():
    client = TestClient(create_app())
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "track/file" in resp.text


def test_track_file_csv():
    import io
    client = TestClient(create_app())
    csv_content = b"id,number\na1,080-38652331\n"
    resp = client.post(
        "/track/file",
        files={"file": ("batch.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["total"] == 1
