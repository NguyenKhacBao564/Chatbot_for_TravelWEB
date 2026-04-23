from fastapi.testclient import TestClient

import server


class FakePipeline:
    def __init__(self):
        self.calls = []
        self.reset_calls = []

    def get_tour_response(self, query, user_id="default_user"):
        self.calls.append((query, user_id))
        return {
            "status": "missing_info",
            "message": "need more info",
            "entities": {},
            "missing_fields": ["time"],
            "tours": [],
            "faq_sources": [],
        }

    def reset_session(self, user_id="default_user"):
        self.reset_calls.append(user_id)


def test_health_endpoint():
    client = TestClient(server.app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_endpoint_passes_user_id():
    fake_pipeline = FakePipeline()
    server.pipeline = fake_pipeline
    client = TestClient(server.app)

    response = client.post(
        "/chat",
        json={"query": "Tôi muốn đi Đà Lạt", "user_id": "user_123"},
    )

    assert response.status_code == 200
    assert fake_pipeline.calls == [("Tôi muốn đi Đà Lạt", "user_123")]
    assert response.json()["status"] == "missing_info"


def test_chat_endpoint_rejects_blank_query():
    server.pipeline = FakePipeline()
    client = TestClient(server.app)

    response = client.post(
        "/chat",
        json={"query": "   ", "user_id": "user_123"},
    )

    assert response.status_code == 422


def test_chat_endpoint_rejects_invalid_user_id():
    server.pipeline = FakePipeline()
    client = TestClient(server.app)

    response = client.post(
        "/chat",
        json={"query": "Tôi muốn đi Đà Lạt", "user_id": "user 123!"},
    )

    assert response.status_code == 422


def test_reset_endpoint_calls_pipeline_reset():
    fake_pipeline = FakePipeline()
    server.pipeline = fake_pipeline
    client = TestClient(server.app)

    response = client.post("/reset", json={"user_id": "user_123"})

    assert response.status_code == 200
    assert fake_pipeline.reset_calls == ["user_123"]
    assert response.json()["status"] == "ok"


def test_health_endpoint_has_local_cors_header():
    server.pipeline = FakePipeline()
    client = TestClient(server.app)

    response = client.get(
        "/health",
        headers={"Origin": "http://localhost:5173"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
