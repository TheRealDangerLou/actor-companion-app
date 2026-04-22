"""Backend tests for Quick Coach feature.

Endpoint: POST /api/projects/{id}/quick-coach
Validates: generation, schema, project-level cache, force-regenerate, error cases.
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://script-breakdown-4.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

# Demo Script project (has SARAH selected + reviewed lines + coach_cache from prior run)
DEMO_PROJECT_ID = "017a5a4f-9d91-4c92-9012-47d1c854d8e9"


@pytest.fixture(scope="session")
def http():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---------- Schema helpers ----------
def _assert_coach_schema(data):
    assert isinstance(data, dict)
    for key in ["casting_intent", "how_to_play_it", "what_to_avoid", "takes"]:
        assert key in data, f"missing '{key}' in coach response"
    assert isinstance(data["casting_intent"], str) and data["casting_intent"].strip()
    assert isinstance(data["how_to_play_it"], str) and data["how_to_play_it"].strip()
    assert isinstance(data["what_to_avoid"], str) and data["what_to_avoid"].strip()
    assert isinstance(data["takes"], list) and 2 <= len(data["takes"]) <= 5
    for t in data["takes"]:
        assert "label" in t and isinstance(t["label"], str) and t["label"].strip()
        assert "direction" in t and isinstance(t["direction"], str) and t["direction"].strip()


# ---------- 1. Cache hit on existing demo project ----------
class TestCacheHit:
    def test_cache_returns_immediately(self, http):
        """Demo project already has coach_cache → second call should be fast."""
        t0 = time.time()
        r = http.post(f"{API}/projects/{DEMO_PROJECT_ID}/quick-coach", json={})
        elapsed = time.time() - t0
        assert r.status_code == 200, r.text
        data = r.json()
        _assert_coach_schema(data)
        # cache should be near-instant (<3s including network latency)
        assert elapsed < 5.0, f"expected cache hit but took {elapsed:.2f}s"

    def test_cache_returns_same_data_on_repeat(self, http):
        """Two consecutive cached calls return identical content."""
        r1 = http.post(f"{API}/projects/{DEMO_PROJECT_ID}/quick-coach", json={})
        r2 = http.post(f"{API}/projects/{DEMO_PROJECT_ID}/quick-coach", json={})
        assert r1.status_code == 200 and r2.status_code == 200
        d1, d2 = r1.json(), r2.json()
        assert d1["casting_intent"] == d2["casting_intent"]
        assert d1["how_to_play_it"] == d2["how_to_play_it"]
        assert d1["what_to_avoid"] == d2["what_to_avoid"]
        assert d1.get("generated_at") == d2.get("generated_at")


# ---------- 2. Error cases ----------
class TestErrorCases:
    def test_404_for_unknown_project(self, http):
        r = http.post(f"{API}/projects/non-existent-{uuid.uuid4().hex}/quick-coach", json={})
        assert r.status_code == 404
        assert "not found" in r.json().get("detail", "").lower()

    def test_400_when_no_character_selected(self, http):
        # Find an existing project that has no selected_character
        projs = http.get(f"{API}/projects").json()
        target = next((p for p in projs if not p.get("selected_character")), None)
        if not target:
            pytest.skip("No project without selected_character available")
        r = http.post(f"{API}/projects/{target['id']}/quick-coach", json={})
        assert r.status_code == 400
        assert "character" in r.json().get("detail", "").lower()


# ---------- 3. force=True regenerates ----------
class TestForceRegenerate:
    def test_force_true_calls_gpt_and_updates_cache(self, http):
        """force=true should make a fresh GPT call → new generated_at timestamp.
        This is slow (5-15s)."""
        # Get current cached generated_at
        r0 = http.post(f"{API}/projects/{DEMO_PROJECT_ID}/quick-coach", json={})
        assert r0.status_code == 200
        old = r0.json()
        old_gen_at = old.get("generated_at")

        # Force regenerate
        t0 = time.time()
        r1 = http.post(f"{API}/projects/{DEMO_PROJECT_ID}/quick-coach",
                       json={"force": True}, timeout=60)
        elapsed = time.time() - t0
        assert r1.status_code == 200, r1.text
        new = r1.json()
        _assert_coach_schema(new)
        new_gen_at = new.get("generated_at")
        # generated_at should have changed
        assert new_gen_at and new_gen_at != old_gen_at, \
            f"generated_at did not change: old={old_gen_at} new={new_gen_at}"
        # Should take at least 1s (real GPT call)
        assert elapsed > 1.0, f"force=true returned too fast ({elapsed:.2f}s) — not a real call?"

    def test_subsequent_call_returns_new_cached_value(self, http):
        """After force=true above, a normal call should return the *new* value."""
        r = http.post(f"{API}/projects/{DEMO_PROJECT_ID}/quick-coach", json={})
        assert r.status_code == 200
        data = r.json()
        _assert_coach_schema(data)
        # Should return cached (already regenerated above)
