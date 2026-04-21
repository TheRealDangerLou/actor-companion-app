"""
Tests for Feature #6 - Line Extraction + Rehearsal Mode backend.
Endpoint: POST /api/projects/{id}/extract-lines
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fallback to frontend .env read
    env_path = "/app/frontend/.env"
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                    break

API = f"{BASE_URL}/api"

MULTI_SCENE_SCRIPT = """INT. LIVING ROOM - DAY

SARAH sits on the couch. JOHN enters.

JOHN
Hey, you're home early.

SARAH
Yeah, meeting got cancelled.

JOHN
Everything okay?

SARAH
Honestly, I'm not sure.

INT. KITCHEN - LATER

Sarah pours coffee.

JOHN
Want to talk about it?

SARAH
Maybe later.

INT. HALLWAY - NIGHT

JOHN
I'm here if you need me.

SARAH
Thank you, John.
"""

SINGLE_SCENE_SCRIPT = """MARIA
Where were you?

TOM
Stuck in traffic.

MARIA
You could have called.

TOM
My phone died.

MARIA
Of course it did.
"""


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _create_project(session, title, script_text):
    """Helper: create project, upload pasted text, clean, confirm, set char."""
    # 1. Create project
    r = session.post(f"{API}/projects", json={
        "title": title, "mode": "audition", "project_type": "horizontal"
    })
    assert r.status_code in (200, 201), f"create project failed: {r.status_code} {r.text}"
    project = r.json()
    pid = project["id"]

    # 2. Upload pasted text (multipart form)
    r = requests.post(
        f"{API}/projects/{pid}/documents",
        data={"pasted_text": script_text, "doc_type": "sides"},
    )
    assert r.status_code in (200, 201), f"paste failed: {r.status_code} {r.text}"
    doc = r.json()
    doc_id = doc["id"]

    # 3. Clean doc (deterministic - no GPT required for paste)
    r = session.post(f"{API}/documents/{doc_id}/clean")
    assert r.status_code == 200, f"clean failed: {r.status_code} {r.text}"

    # Poll until cleaned_text is available (clean may be async)
    cleaned_text = ""
    for _ in range(30):
        r = session.get(f"{API}/documents/{doc_id}")
        if r.status_code == 200 and r.json().get("cleaned_text"):
            cleaned_text = r.json()["cleaned_text"]
            break
        time.sleep(1)
    if not cleaned_text:
        # fallback: use raw
        cleaned_text = script_text

    # 4. Confirm doc with cleaned_text
    r = session.post(f"{API}/documents/{doc_id}/confirm", json={"cleaned_text": cleaned_text})
    assert r.status_code == 200, f"confirm failed: {r.status_code} {r.text}"

    return pid, doc_id


def _set_character(session, pid, char):
    r = session.put(f"{API}/projects/{pid}", json={"selected_character": char})
    assert r.status_code == 200, f"set char failed: {r.status_code} {r.text}"


def _cleanup(session, pid):
    try:
        session.delete(f"{API}/projects/{pid}")
    except Exception:
        pass


# --- Test Cases ---

def test_health():
    r = requests.get(f"{API}/")
    assert r.status_code == 200


def test_404_unknown_project(session):
    r = session.post(f"{API}/projects/nonexistent-id-xyz/extract-lines")
    assert r.status_code == 404


def test_400_no_character(session):
    pid, _ = _create_project(session, "TEST_NoChar", MULTI_SCENE_SCRIPT)
    try:
        r = session.post(f"{API}/projects/{pid}/extract-lines")
        assert r.status_code == 400
        assert "character" in r.json().get("detail", "").lower()
    finally:
        _cleanup(session, pid)


def test_400_no_confirmed_docs(session):
    # Create project, no docs, set character
    r = session.post(f"{API}/projects", json={
        "title": "TEST_NoConfirm", "mode": "audition", "project_type": "horizontal"
    })
    assert r.status_code in (200, 201)
    pid = r.json()["id"]
    try:
        _set_character(session, pid, "SARAH")
        r = session.post(f"{API}/projects/{pid}/extract-lines")
        assert r.status_code == 400
    finally:
        _cleanup(session, pid)


def test_multi_scene_extraction_sarah(session):
    pid, _ = _create_project(session, "TEST_MultiScene", MULTI_SCENE_SCRIPT)
    try:
        _set_character(session, pid, "SARAH")
        r = session.post(f"{API}/projects/{pid}/extract-lines")
        assert r.status_code == 200, r.text
        data = r.json()

        # Response shape
        assert data["project_id"] == pid
        assert data["character"] == "SARAH"
        assert "full_text" in data
        assert isinstance(data["full_text"], str) and len(data["full_text"]) > 0
        assert "scenes" in data
        assert isinstance(data["scenes"], list)
        assert data["total_lines"] >= 4  # SARAH has 4 dialogue blocks in fixture

        # Should have 3 scenes
        assert len(data["scenes"]) == 3, f"expected 3 scenes, got {len(data['scenes'])}"

        # Scene headings should be INT./EXT. lines
        headings = [s["heading"] for s in data["scenes"]]
        assert any("LIVING ROOM" in h for h in headings)
        assert any("KITCHEN" in h for h in headings)
        assert any("HALLWAY" in h for h in headings)

        # First line of first scene: cue should be "(Scene start)" since SARAH speaks first
        scene1 = data["scenes"][0]
        assert len(scene1["line_pairs"]) >= 1
        first_pair = scene1["line_pairs"][0]
        # SARAH's first line "Yeah, meeting got cancelled." comes after JOHN, so cue_speaker=JOHN
        # But first appearance in scene (SARAH) -> JOHN spoke first.
        # Per spec: cue = last different speaker. JOHN's "Hey, you're home early."
        assert first_pair["cue_speaker"] == "JOHN"
        assert "home early" in first_pair["cue_text"].lower() or "(scene start)" in first_pair["cue_text"].lower()
        assert "meeting got cancelled" in first_pair["line_text"].lower()

        # Validate each pair has required fields
        for scene in data["scenes"]:
            for pair in scene["line_pairs"]:
                assert "cue_speaker" in pair
                assert "cue_text" in pair
                assert "line_text" in pair
                assert "index" in pair
                assert pair["line_text"]  # non-empty
    finally:
        _cleanup(session, pid)


def test_first_line_cue_when_character_speaks_first(session):
    # Script where target character (TOM) speaks first in a scene
    script = """INT. OFFICE - DAY

TOM
Good morning everyone.

MARIA
Good morning, Tom.

TOM
Let's start the meeting.
"""
    pid, _ = _create_project(session, "TEST_FirstLine", script)
    try:
        _set_character(session, pid, "TOM")
        r = session.post(f"{API}/projects/{pid}/extract-lines")
        assert r.status_code == 200
        data = r.json()
        assert data["total_lines"] == 2
        scene = data["scenes"][0]
        # TOM's first line - no prior speaker -> "(Scene start)"
        first = scene["line_pairs"][0]
        assert first["cue_text"] == "(Scene start)"
        assert first["cue_speaker"] == ""
        # TOM's second line - cue should be MARIA
        second = scene["line_pairs"][1]
        assert second["cue_speaker"] == "MARIA"
        assert "good morning, tom" in second["cue_text"].lower()
    finally:
        _cleanup(session, pid)


def test_single_scene_full_script(session):
    pid, _ = _create_project(session, "TEST_SingleScene", SINGLE_SCENE_SCRIPT)
    try:
        _set_character(session, pid, "MARIA")
        r = session.post(f"{API}/projects/{pid}/extract-lines")
        assert r.status_code == 200
        data = r.json()
        assert data["total_lines"] == 3  # MARIA has 3 lines
        assert len(data["scenes"]) == 1
        assert data["scenes"][0]["heading"] == "Full Script"
        assert data["scenes"][0]["scene_number"] == 1
        # First line "(Scene start)" since MARIA speaks first
        first = data["scenes"][0]["line_pairs"][0]
        assert first["cue_text"] == "(Scene start)"
    finally:
        _cleanup(session, pid)


def test_multi_document_combined(session):
    pid, _ = _create_project(session, "TEST_MultiDoc", MULTI_SCENE_SCRIPT)
    try:
        # Upload a 2nd doc
        extra = """INT. GARDEN - MORNING

SARAH
I needed this air.

JOHN
You deserve peace.

SARAH
Thanks, really.
"""
        r = requests.post(
            f"{API}/projects/{pid}/documents",
            data={"pasted_text": extra, "doc_type": "sides"},
        )
        assert r.status_code in (200, 201)
        doc2_id = r.json()["id"]
        session.post(f"{API}/documents/{doc2_id}/clean")
        cleaned2 = ""
        for _ in range(30):
            g = session.get(f"{API}/documents/{doc2_id}")
            if g.status_code == 200 and g.json().get("cleaned_text"):
                cleaned2 = g.json()["cleaned_text"]
                break
            time.sleep(1)
        if not cleaned2:
            cleaned2 = extra
        session.post(f"{API}/documents/{doc2_id}/confirm", json={"cleaned_text": cleaned2})

        _set_character(session, pid, "SARAH")
        r = session.post(f"{API}/projects/{pid}/extract-lines")
        assert r.status_code == 200
        data = r.json()
        # Combined should have >=4 scenes (3 + 1)
        assert len(data["scenes"]) >= 4
        headings = " ".join(s["heading"] for s in data["scenes"])
        assert "GARDEN" in headings
    finally:
        _cleanup(session, pid)


def test_full_text_field_returned(session):
    pid, _ = _create_project(session, "TEST_FullText", MULTI_SCENE_SCRIPT)
    try:
        _set_character(session, pid, "SARAH")
        r = session.post(f"{API}/projects/{pid}/extract-lines")
        assert r.status_code == 200
        data = r.json()
        assert "full_text" in data
        assert "SARAH" in data["full_text"]
        assert "JOHN" in data["full_text"]
    finally:
        _cleanup(session, pid)
