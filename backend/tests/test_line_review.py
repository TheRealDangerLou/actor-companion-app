"""Tests for reviewed-lines endpoints (Feature #6.5 Review My Lines)."""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fallback to frontend .env read
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
    except Exception:
        pass

API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture
def temp_project(client):
    payload = {"title": f"TEST_Review_{uuid.uuid4().hex[:6]}", "project_type": "audition"}
    r = client.post(f"{API}/projects", json=payload)
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    yield pid
    client.delete(f"{API}/projects/{pid}")


SAMPLE = {
    "scenes": [
        {
            "scene_number": 1,
            "heading": "INT. LIVING ROOM - DAY",
            "line_pairs": [
                {"cue_speaker": "JOHN", "cue_text": "Hello.", "line_text": "Hi there."},
                {"cue_speaker": "JOHN", "cue_text": "Are you OK?", "line_text": "I'm fine."},
            ],
        },
        {
            "scene_number": 2,
            "heading": "EXT. STREET - NIGHT",
            "line_pairs": [
                {"cue_speaker": "MARY", "cue_text": "Leaving?", "line_text": "Goodbye."},
            ],
        },
    ]
}


class TestReviewedLinesSaveAndGet:
    def test_save_then_get_roundtrip(self, client, temp_project):
        r = client.put(f"{API}/projects/{temp_project}/reviewed-lines", json=SAMPLE)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "ok"
        assert body["total_lines"] == 3
        assert body["scene_count"] == 2

        g = client.get(f"{API}/projects/{temp_project}/reviewed-lines")
        assert g.status_code == 200
        data = g.json()
        assert data["total_lines"] == 3
        assert len(data["reviewed_lines"]) == 2
        assert data["reviewed_lines"][0]["heading"] == "INT. LIVING ROOM - DAY"
        assert data["reviewed_lines"][0]["line_pairs"][0]["line_text"] == "Hi there."

    def test_get_returns_null_when_not_saved(self, client, temp_project):
        g = client.get(f"{API}/projects/{temp_project}/reviewed-lines")
        assert g.status_code == 200
        assert g.json()["reviewed_lines"] is None
        assert g.json()["total_lines"] == 0

    def test_empty_line_text_pairs_are_stripped(self, client, temp_project):
        payload = {
            "scenes": [
                {
                    "scene_number": 1,
                    "heading": "INT. ROOM",
                    "line_pairs": [
                        {"cue_speaker": "X", "cue_text": "c1", "line_text": "keep me"},
                        {"cue_speaker": "X", "cue_text": "c2", "line_text": "   "},
                        {"cue_speaker": "X", "cue_text": "c3", "line_text": ""},
                    ],
                }
            ]
        }
        r = client.put(f"{API}/projects/{temp_project}/reviewed-lines", json=payload)
        assert r.status_code == 200
        assert r.json()["total_lines"] == 1

        g = client.get(f"{API}/projects/{temp_project}/reviewed-lines").json()
        assert len(g["reviewed_lines"][0]["line_pairs"]) == 1
        assert g["reviewed_lines"][0]["line_pairs"][0]["line_text"] == "keep me"

    def test_empty_scenes_are_stripped(self, client, temp_project):
        payload = {
            "scenes": [
                {"scene_number": 1, "heading": "A", "line_pairs": []},
                {
                    "scene_number": 2,
                    "heading": "B",
                    "line_pairs": [
                        {"cue_speaker": "X", "cue_text": "", "line_text": ""},
                    ],
                },
                {
                    "scene_number": 3,
                    "heading": "C",
                    "line_pairs": [
                        {"cue_speaker": "X", "cue_text": "c", "line_text": "real line"},
                    ],
                },
            ]
        }
        r = client.put(f"{API}/projects/{temp_project}/reviewed-lines", json=payload)
        assert r.status_code == 200
        body = r.json()
        assert body["scene_count"] == 1
        assert body["total_lines"] == 1

        g = client.get(f"{API}/projects/{temp_project}/reviewed-lines").json()
        assert len(g["reviewed_lines"]) == 1
        assert g["reviewed_lines"][0]["heading"] == "C"

    def test_put_unknown_project_returns_404(self, client):
        r = client.put(f"{API}/projects/does-not-exist-xyz/reviewed-lines", json=SAMPLE)
        assert r.status_code == 404

    def test_get_unknown_project_returns_404(self, client):
        r = client.get(f"{API}/projects/does-not-exist-xyz/reviewed-lines")
        assert r.status_code == 404

    def test_put_no_scenes_returns_400(self, client, temp_project):
        r = client.put(f"{API}/projects/{temp_project}/reviewed-lines", json={"scenes": []})
        assert r.status_code == 400

    def test_update_overwrites_previous(self, client, temp_project):
        # First save
        client.put(f"{API}/projects/{temp_project}/reviewed-lines", json=SAMPLE)
        # Overwrite with fewer lines
        new_payload = {
            "scenes": [
                {
                    "scene_number": 1,
                    "heading": "INT. NEW",
                    "line_pairs": [
                        {"cue_speaker": "Z", "cue_text": "cue", "line_text": "only line"},
                    ],
                }
            ]
        }
        r = client.put(f"{API}/projects/{temp_project}/reviewed-lines", json=new_payload)
        assert r.status_code == 200
        assert r.json()["total_lines"] == 1

        g = client.get(f"{API}/projects/{temp_project}/reviewed-lines").json()
        assert g["total_lines"] == 1
        assert g["reviewed_lines"][0]["heading"] == "INT. NEW"
        assert g["reviewed_lines"][0]["line_pairs"][0]["line_text"] == "only line"
