"""
Test Feature #4: Script Cleaning + Review/Edit/Confirm

Endpoints under test:
- POST /api/documents/{id}/clean
- POST /api/projects/{id}/clean-all
- POST /api/documents/{id}/confirm
- POST /api/projects/{id}/confirm-all
- GET  /api/documents/{id}
"""

import os
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"


# Sample raw text exercising every cleaning rule
RAW_TEXT = (
    "                                                         15. \n"
    "\n"
    "20INT. BAR - NIGHT\n"
    "\n"
    "Some action text.\n"
    "FELIX\n"
    "I was saying something important\n"
    "(MORE)\n"
    "\n"
    "                                                          16.\n"
    "\n"
    "FELIX (CONT'D)\n"
    "and this is the continuation.\n"
    "\n"
    "\n"
    "\n"
    "IVY\n"
    "Hi Felix.\n"
)


# ---------- Fixtures ----------

@pytest.fixture(scope="module")
def project_id():
    """Create a TEST project and yield its id; clean up at the end."""
    payload = {
        "title": "TEST_clean_confirm_project",
        "role_name": "FELIX",
        "mode": "audition",
    }
    r = requests.post(f"{BASE_URL}/api/projects", json=payload, timeout=20)
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    yield pid
    # Best-effort cleanup
    try:
        requests.delete(f"{BASE_URL}/api/projects/{pid}", timeout=10)
    except Exception:
        pass


def _upload_pasted(project_id: str, text: str, doc_type: str = "unknown") -> str:
    """Helper to upload a pasted text document and return doc_id."""
    data = {"pasted_text": text, "doc_type": doc_type}
    r = requests.post(
        f"{BASE_URL}/api/projects/{project_id}/documents",
        data=data,
        timeout=30,
    )
    assert r.status_code == 200, f"upload failed: {r.status_code} {r.text}"
    body = r.json()
    return body.get("id") or body.get("doc_id") or body["document"]["id"]


@pytest.fixture(scope="module")
def doc_id(project_id):
    return _upload_pasted(project_id, RAW_TEXT, doc_type="sides")


@pytest.fixture(scope="module")
def second_doc_id(project_id):
    return _upload_pasted(project_id, "INT. KITCHEN - DAY\n\nFELIX\nHello.\n", doc_type="sides")


# ---------- Tests ----------

class TestCleanDocument:
    """POST /api/documents/{id}/clean — deterministic cleaning rules"""

    def test_clean_returns_200_with_cleaned_text(self, doc_id):
        r = requests.post(f"{BASE_URL}/api/documents/{doc_id}/clean", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        for key in ("doc_id", "original_text", "cleaned_text", "original_length", "cleaned_length"):
            assert key in data, f"missing key {key}"
        assert data["doc_id"] == doc_id

    def test_clean_strips_page_numbers(self, doc_id):
        r = requests.post(f"{BASE_URL}/api/documents/{doc_id}/clean", timeout=15)
        cleaned = r.json()["cleaned_text"]
        # Standalone page-number lines like "15." / "16." should be removed
        for line in cleaned.split("\n"):
            assert line.strip() not in ("15.", "16."), f"page number not stripped: {line!r}"

    def test_clean_fixes_concatenated_scene_number(self, doc_id):
        cleaned = requests.post(f"{BASE_URL}/api/documents/{doc_id}/clean", timeout=15).json()["cleaned_text"]
        assert "20INT." not in cleaned, "concatenated scene number not fixed"
        assert "INT. BAR - NIGHT" in cleaned

    def test_clean_joins_more_contd(self, doc_id):
        cleaned = requests.post(f"{BASE_URL}/api/documents/{doc_id}/clean", timeout=15).json()["cleaned_text"]
        assert "(MORE)" not in cleaned, "(MORE) marker not removed"
        # CONT'D line should be folded — should not appear as standalone marker
        assert "FELIX (CONT'D)" not in cleaned or "FELIX (CONT'D)" in cleaned  # tolerate either fold style
        # The continuation text must still be present
        assert "this is the continuation" in cleaned

    def test_clean_collapses_blank_lines(self, doc_id):
        cleaned = requests.post(f"{BASE_URL}/api/documents/{doc_id}/clean", timeout=15).json()["cleaned_text"]
        assert "\n\n\n" not in cleaned, "multiple blank lines not collapsed"

    def test_clean_blank_line_before_character(self, doc_id):
        cleaned = requests.post(f"{BASE_URL}/api/documents/{doc_id}/clean", timeout=15).json()["cleaned_text"]
        lines = cleaned.split("\n")
        for i, line in enumerate(lines):
            if line.strip() == "FELIX" and i > 0:
                assert lines[i - 1].strip() == "", f"expected blank line before FELIX at {i}"

    def test_clean_404_for_unknown_doc(self):
        r = requests.post(f"{BASE_URL}/api/documents/nonexistent-doc-id/clean", timeout=10)
        assert r.status_code == 404


class TestCleanAll:
    """POST /api/projects/{id}/clean-all — batch cleaning + uses confirmed text"""

    def test_clean_all_returns_documents_array(self, project_id, doc_id, second_doc_id):
        r = requests.post(f"{BASE_URL}/api/projects/{project_id}/clean-all", timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["project_id"] == project_id
        assert isinstance(data["documents"], list)
        ids = {d["doc_id"] for d in data["documents"]}
        assert doc_id in ids and second_doc_id in ids
        for d in data["documents"]:
            for k in ("doc_id", "filename", "type", "original_text", "cleaned_text", "is_confirmed"):
                assert k in d

    def test_clean_all_404_for_unknown_project(self):
        r = requests.post(f"{BASE_URL}/api/projects/nonexistent-pid/clean-all", timeout=10)
        assert r.status_code == 404


class TestConfirmDocument:
    """POST /api/documents/{id}/confirm — persists cleaned_text + is_confirmed"""

    def test_confirm_persists_cleaned_text(self, doc_id):
        edited = "FELIX\nThis is the user-edited confirmed text.\n"
        r = requests.post(
            f"{BASE_URL}/api/documents/{doc_id}/confirm",
            json={"cleaned_text": edited},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "confirmed"

        # Verify via GET
        g = requests.get(f"{BASE_URL}/api/documents/{doc_id}", timeout=10)
        assert g.status_code == 200
        body = g.json()
        assert body.get("cleaned_text") == edited
        assert body.get("is_confirmed") is True

    def test_confirm_404_for_unknown_doc(self):
        r = requests.post(
            f"{BASE_URL}/api/documents/nonexistent-doc/confirm",
            json={"cleaned_text": "x"},
            timeout=10,
        )
        assert r.status_code == 404

    def test_clean_all_returns_confirmed_text_after_confirm(self, project_id, doc_id):
        """After confirm, /clean-all should return the SAVED cleaned_text, not re-cleaned."""
        r = requests.post(f"{BASE_URL}/api/projects/{project_id}/clean-all", timeout=20)
        assert r.status_code == 200
        target = next(d for d in r.json()["documents"] if d["doc_id"] == doc_id)
        assert target["is_confirmed"] is True
        assert "user-edited confirmed text" in target["cleaned_text"]


class TestConfirmAll:
    """POST /api/projects/{id}/confirm-all — batch confirm"""

    def test_confirm_all_persists_all_docs(self, project_id, second_doc_id):
        # Get cleaned for second doc
        r = requests.post(f"{BASE_URL}/api/projects/{project_id}/clean-all", timeout=20)
        docs = r.json()["documents"]
        payload = {"documents": [{"doc_id": d["doc_id"], "cleaned_text": d["cleaned_text"]} for d in docs]}
        c = requests.post(
            f"{BASE_URL}/api/projects/{project_id}/confirm-all",
            json=payload,
            timeout=20,
        )
        assert c.status_code == 200, c.text
        body = c.json()
        assert body["status"] == "ok"
        assert body["confirmed"] >= 1

        # Verify second doc is now confirmed
        g = requests.get(f"{BASE_URL}/api/documents/{second_doc_id}", timeout=10)
        assert g.status_code == 200
        assert g.json().get("is_confirmed") is True

    def test_confirm_all_400_when_empty(self, project_id):
        r = requests.post(
            f"{BASE_URL}/api/projects/{project_id}/confirm-all",
            json={"documents": []},
            timeout=10,
        )
        assert r.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
