from fastapi.testclient import TestClient

import server


class FakePipeline:
    def __init__(self):
        self.calls = []

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

