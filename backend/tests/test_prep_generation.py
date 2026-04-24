"""
Backend tests for Feature #10: Prep Generation
- POST /api/projects/{id}/prep-generation (cached, force, error paths)
- PUT /api/projects/{id} (selected_character clears prep_cache AND coach_cache)
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://script-breakdown-4.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

NIGHT_SHIFT_ID = "4006936f-a584-430c-9452-95ba2babdb67"  # breakdown path
DEMO_SCRIPT_ID = "017a5a4f-9d91-4c92-9012-47d1c854d8e9"  # script path


@pytest.fixture(scope="module")
def api_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def seeded_project(api_client):
    """Create a fresh project with confirmed breakdown doc and selected_character."""
    name = f"TEST_prep_{uuid.uuid4().hex[:8]}"
    # 1. create
    r = api_client.post(f"{API}/projects", json={
        "title": name,
        "role_name": "Detective Maya",
        "mode": "full_script",
        "audition_format": "self-tape",
    })
    assert r.status_code in (200, 201), r.text
    pid = r.json()["id"]

    # 2. upload/paste doc (multipart form)
    sides_text = (
        "CASTING BREAKDOWN\n\n"
        "ROLE: Detective Maya Chen — early 30s, sharp, Asian-American homicide detective.\n"
        "WARDROBE: professional, dark tones, minimal jewelry.\n"
        "SELF-TAPE: medium close-up, neutral wall, eyeline just off camera.\n"
        "TONE: grounded, contained, restrained anger.\n"
    )
    # Use a bare requests POST (multipart form, no JSON header)
    r = requests.post(
        f"{API}/projects/{pid}/documents",
        data={"pasted_text": sides_text, "doc_type": "sides"},
    )
    assert r.status_code in (200, 201), r.text
    doc_id = r.json()["id"]

    # 3. classify as sides (endpoint is /documents/{doc_id}/type)
    requests.put(f"{API}/documents/{doc_id}/type", json={"type": "sides"})

    # 4. confirm all docs — expects {documents: [{doc_id, cleaned_text}]}
    # Fetch the document to get its cleaned_text
    doc_resp = requests.get(f"{API}/projects/{pid}/documents")
    docs_list = doc_resp.json() if doc_resp.status_code == 200 else []
    cleaned = ""
    for d in docs_list:
        if d.get("id") == doc_id:
            cleaned = d.get("cleaned_text") or d.get("original_text") or sides_text
            break
    if not cleaned:
        cleaned = sides_text
    r = requests.post(
        f"{API}/projects/{pid}/confirm-all",
        json={"documents": [{"doc_id": doc_id, "cleaned_text": cleaned}]},
    )
    assert r.status_code == 200, r.text

    # 5. set selected_character
    r = api_client.put(f"{API}/projects/{pid}", json={"selected_character": "Detective Maya"})
    assert r.status_code == 200, r.text

    yield pid

    # cleanup
    try:
        api_client.delete(f"{API}/projects/{pid}")
    except Exception:
        pass


# ---------- Error paths ----------

class TestPrepErrorCases:
    def test_unknown_project_returns_404(self, api_client):
        r = api_client.post(f"{API}/projects/does-not-exist-xyz/prep-generation", json={})
        assert r.status_code == 404

    def test_no_character_returns_400(self, api_client):
        # create project with no character
        name = f"TEST_prep_nochar_{uuid.uuid4().hex[:6]}"
        r = api_client.post(f"{API}/projects", json={"title": name, "role_name": "X", "mode": "full_script"})
        pid = r.json()["id"]
        try:
            r = api_client.post(f"{API}/projects/{pid}/prep-generation", json={})
            assert r.status_code == 400
            assert "character" in r.text.lower()
        finally:
            api_client.delete(f"{API}/projects/{pid}")

    def test_no_confirmed_docs_returns_400(self, api_client):
        name = f"TEST_prep_nodocs_{uuid.uuid4().hex[:6]}"
        r = api_client.post(f"{API}/projects", json={"title": name, "role_name": "X", "mode": "full_script"})
        pid = r.json()["id"]
        try:
            api_client.put(f"{API}/projects/{pid}", json={"selected_character": "X"})
            r = api_client.post(f"{API}/projects/{pid}/prep-generation", json={})
            assert r.status_code == 400
            assert "document" in r.text.lower()
        finally:
            api_client.delete(f"{API}/projects/{pid}")


# ---------- Happy path + caching ----------

class TestPrepHappyPath:
    def test_generate_and_cache_and_force(self, api_client, seeded_project):
        pid = seeded_project

        # first call — may be cache (if previous test) or fresh
        r1 = api_client.post(f"{API}/projects/{pid}/prep-generation", json={}, timeout=60)
        assert r1.status_code == 200, r1.text
        data1 = r1.json()

        # Schema assertions
        assert "wardrobe" in data1 and isinstance(data1["wardrobe"], list)
        assert "self_tape_setup" in data1 and isinstance(data1["self_tape_setup"], dict)
        assert "action_items" in data1 and isinstance(data1["action_items"], list)
        assert "generated_at" in data1
        assert data1.get("character") == "Detective Maya"
        # At least some content
        assert len(data1["wardrobe"]) > 0 or len(data1["action_items"]) > 0
        setup = data1["self_tape_setup"]
        # At least some setup keys present
        assert any(k in setup for k in ("framing", "backdrop", "eyeline", "energy_note"))

        # Second call — cache hit, same generated_at, fast (<3s)
        t0 = time.time()
        r2 = api_client.post(f"{API}/projects/{pid}/prep-generation", json={}, timeout=30)
        elapsed = time.time() - t0
        assert r2.status_code == 200
        data2 = r2.json()
        assert data2["generated_at"] == data1["generated_at"], "Cache should return same generated_at"
        assert elapsed < 3.0, f"Cache call took {elapsed:.2f}s — expected <3s"

        # Verify cache persists on project doc
        proj = api_client.get(f"{API}/projects/{pid}").json()
        assert proj.get("prep_cache") is not None
        assert proj["prep_cache"]["generated_at"] == data1["generated_at"]

        # Force regenerate — new generated_at
        r3 = api_client.post(f"{API}/projects/{pid}/prep-generation", json={"force": True}, timeout=60)
        assert r3.status_code == 200
        data3 = r3.json()
        assert data3["generated_at"] != data1["generated_at"], "force=true should yield new generated_at"


# ---------- Cache invalidation on character change ----------

class TestCharacterChangeInvalidation:
    def test_character_change_clears_prep_and_coach_caches(self, api_client, seeded_project):
        pid = seeded_project

        # Ensure prep_cache exists
        r = api_client.post(f"{API}/projects/{pid}/prep-generation", json={}, timeout=60)
        assert r.status_code == 200

        # Seed a coach_cache too via quick-coach
        try:
            api_client.post(f"{API}/projects/{pid}/quick-coach", json={}, timeout=60)
        except Exception:
            pass

        # Verify both caches likely exist
        proj_before = api_client.get(f"{API}/projects/{pid}").json()
        assert proj_before.get("prep_cache") is not None

        # Change character
        r = api_client.put(f"{API}/projects/{pid}", json={"selected_character": "Someone Else"})
        assert r.status_code == 200

        # Verify both caches cleared
        proj_after = api_client.get(f"{API}/projects/{pid}").json()
        assert proj_after.get("prep_cache") in (None, {}), f"prep_cache should be cleared, got {proj_after.get('prep_cache')}"
        assert proj_after.get("coach_cache") in (None, {}), f"coach_cache should be cleared, got {proj_after.get('coach_cache')}"
        assert proj_after.get("selected_character") == "Someone Else"
