from fastapi.testclient import TestClient

from app.main import app


def test_metrics_endpoint_returns_acceptance_gate_shape():
    client = TestClient(app)
    response = client.get("/metrics")
    assert response.status_code == 200
    payload = response.json()
    assert "conversion_rate" in payload
    assert "visitors" in payload
    assert payload["store_id"] == "ST1008"
