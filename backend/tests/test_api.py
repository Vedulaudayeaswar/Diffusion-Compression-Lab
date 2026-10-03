from fastapi.testclient import TestClient

from backend.main import app


def test_health_and_status_endpoints():
    client = TestClient(app)
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/api/system/status").json()["status"] == "online"
    status = client.get("/api/model/status").json()
    assert status["model_id"] == "sd-research/stable-diffusion-2-1-base"
