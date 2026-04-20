"""Tests for Character Detection feature (Feature #5)"""
import os
import requests
import pytest

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://script-breakdown-4.preview.emergentagent.com').rstrip('/')

SCRIPT_TEXT = """INT. POLICE STATION - DAY

SARAH and MARK enter the room. DETECTIVE JONES looks up.

SARAH
I need to talk to you about the case.

MARK
She's right. We have new information.

DETECTIVE JONES
Sit down. Both of you.

SARAH (V.O.)
I knew this would be difficult.

MARK (CONT'D)
We found the evidence at the scene.

CUT TO:

EXT. PARKING LOT - NIGHT

SARAH
Is this where it happened?

DETECTIVE JONES
Yes. Right here.

MARK
We need to be careful.

SARAH (O.S.)
I see something over there.

FADE OUT.

INT. SARAH'S APARTMENT - LATER

SARAH
This is my place.

MARK
Nice apartment.

SARAH (CONT'D)
Thanks.
"""


def _create_project_with_text(title, text):
    """Helper: create project, add document via Form, confirm with cleaned_text."""
    r = requests.post(f"{BASE_URL}/api/projects", json={"title": title, "mode": "audition"})
    assert r.status_code in (200, 201), r.text
    pid = r.json()["id"]

    # Upload via multipart form (pasted_text)
    r = requests.post(
        f"{BASE_URL}/api/projects/{pid}/documents",
        data={"pasted_text": text, "doc_type": "sides"},
    )
    assert r.status_code in (200, 201), r.text
    doc = r.json()
    doc_id = doc.get("id") or doc.get("doc_id")
    assert doc_id, f"No doc id in {doc}"

    # Confirm with cleaned_text = original text
    r = requests.post(
        f"{BASE_URL}/api/documents/{doc_id}/confirm",
        json={"cleaned_text": text},
    )
    assert r.status_code in (200, 204), r.text
    return pid


@pytest.fixture(scope="module")
def project_id():
    pid = _create_project_with_text("TEST_CharDetect", SCRIPT_TEXT)
    yield pid
    requests.delete(f"{BASE_URL}/api/projects/{pid}")


def test_detect_characters_basic(project_id):
    """Detect characters returns ranked list."""
    r = requests.post(f"{BASE_URL}/api/projects/{project_id}/detect-characters")
    assert r.status_code == 200, r.text
    data = r.json()
    assert "characters" in data
    chars = data["characters"]
    names = [c["name"] for c in chars]

    # Expect SARAH, MARK, DETECTIVE JONES detected
    assert "SARAH" in names, f"SARAH missing in {names}"
    assert "MARK" in names, f"MARK missing in {names}"
    assert "DETECTIVE JONES" in names, f"DETECTIVE JONES missing in {names}"


def test_detect_characters_normalizes_variants(project_id):
    """Variants like (V.O.), (CONT'D), (O.S.) should be normalized."""
    r = requests.post(f"{BASE_URL}/api/projects/{project_id}/detect-characters")
    data = r.json()
    names = [c["name"] for c in data["characters"]]
    # Should NOT contain variants
    for variant in ["SARAH (V.O.)", "SARAH (CONT'D)", "SARAH (O.S.)", "MARK (CONT'D)"]:
        assert variant not in names, f"Variant {variant} should be normalized"


def test_detect_characters_excludes_scene_headings(project_id):
    """Scene headings INT./EXT. and transitions FADE/CUT should not be characters."""
    r = requests.post(f"{BASE_URL}/api/projects/{project_id}/detect-characters")
    names = [c["name"] for c in r.json()["characters"]]
    for bad in ["INT.", "EXT.", "FADE OUT.", "CUT TO:", "FADE OUT", "CUT TO"]:
        assert bad not in names, f"Should reject structural marker: {bad}"
    # No name should start with INT or EXT
    for n in names:
        assert not n.startswith("INT."), n
        assert not n.startswith("EXT."), n


def test_detect_characters_ranked_by_frequency(project_id):
    """Characters should be ranked by line count desc, with SARAH typically having most."""
    r = requests.post(f"{BASE_URL}/api/projects/{project_id}/detect-characters")
    chars = r.json()["characters"]
    counts = [c["line_count"] for c in chars]
    assert counts == sorted(counts, reverse=True), f"Not sorted desc: {counts}"
    # SARAH should be top with the most lines
    assert chars[0]["name"] == "SARAH", f"Expected SARAH at top, got {chars[0]['name']}"


def test_detect_characters_no_confirmed_returns_400():
    """If no confirmed documents exist, should return 400."""
    # Create project with no confirmed doc
    r = requests.post(f"{BASE_URL}/api/projects", json={"title": "TEST_NoConfirm", "mode": "audition"})
    pid = r.json()["id"]
    try:
        r = requests.post(f"{BASE_URL}/api/projects/{pid}/detect-characters")
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"
    finally:
        requests.delete(f"{BASE_URL}/api/projects/{pid}")


def test_detect_characters_unknown_project_returns_404():
    """Unknown project id should return 404."""
    r = requests.post(f"{BASE_URL}/api/projects/nonexistent-id-12345/detect-characters")
    assert r.status_code == 404, f"Expected 404, got {r.status_code}"


def test_put_project_persists_selected_character(project_id):
    """PUT project with selected_character should persist."""
    r = requests.put(f"{BASE_URL}/api/projects/{project_id}", json={
        "selected_character": "SARAH",
    })
    assert r.status_code in (200, 204), r.text

    # Verify persistence with GET
    r = requests.get(f"{BASE_URL}/api/projects/{project_id}")
    assert r.status_code == 200
    assert r.json().get("selected_character") == "SARAH"


def test_multi_doc_aggregation():
    """Characters counted across all confirmed docs."""
    # Create project
    r = requests.post(f"{BASE_URL}/api/projects", json={"title": "TEST_MultiDoc", "mode": "audition"})
    pid = r.json()["id"]
    try:
        # Add doc 1
        doc1 = "INT. ROOM\n\nALICE\nHello.\n\nBOB\nHi.\n"
        r = requests.post(f"{BASE_URL}/api/projects/{pid}/documents",
                          data={"pasted_text": doc1, "doc_type": "sides"})
        assert r.status_code in (200, 201), r.text
        d1_id = r.json().get("id") or r.json().get("doc_id")
        requests.post(f"{BASE_URL}/api/documents/{d1_id}/confirm", json={"cleaned_text": doc1})

        # Add doc 2
        doc2 = "INT. CAFE\n\nALICE\nAgain.\n\nALICE\nMore.\n\nCAROL\nHey.\n"
        r = requests.post(f"{BASE_URL}/api/projects/{pid}/documents",
                          data={"pasted_text": doc2, "doc_type": "sides"})
        assert r.status_code in (200, 201), r.text
        d2_id = r.json().get("id") or r.json().get("doc_id")
        requests.post(f"{BASE_URL}/api/documents/{d2_id}/confirm", json={"cleaned_text": doc2})

        # Detect
        r = requests.post(f"{BASE_URL}/api/projects/{pid}/detect-characters")
        assert r.status_code == 200, r.text
        chars = r.json()["characters"]
        by_name = {c["name"]: c["line_count"] for c in chars}
        assert by_name.get("ALICE", 0) == 3, f"ALICE expected 3, got {by_name}"
        assert by_name.get("BOB", 0) == 1, f"BOB expected 1, got {by_name}"
        assert by_name.get("CAROL", 0) == 1, f"CAROL expected 1, got {by_name}"
        assert chars[0]["name"] == "ALICE"
    finally:
        requests.delete(f"{BASE_URL}/api/projects/{pid}")
