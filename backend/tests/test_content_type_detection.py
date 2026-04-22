"""Tests for content-type detection + breakdown extraction + dual-path Quick Coach."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://script-breakdown-4.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

BREAKDOWN_TEXT = (
    "ROLE\nJack Martinez\n\n"
    "CHARACTER DESCRIPTION\nLate 20s, Latino, quiet intensity. A man who has been carrying a secret for years and is finally about to break under its weight. Grounded, real, lived-in.\n\n"
    "CASTING NOTES\nLooking for grounded and real. No big choices. We want to feel the weight of his history without him telling us anything. Less is more.\n\n"
    "SELF-TAPE INSTRUCTIONS\nMedium close-up framing. Solid neutral background. Quiet room. One reader off-camera left. Slate name and height at the head.\n"
)

SCRIPT_TEXT = (
    "INT. OFFICE - DAY\n\n"
    "SARAH\nWe need to talk.\n\n"
    "MARK\nAbout what?\n\n"
    "SARAH\nYou know what.\n\n"
    "MARK\nI really don't.\n\n"
    "SARAH\nThe missing files. They were on your desk yesterday.\n\n"
    "MARK\nThat doesn't mean anything.\n"
)

MONOLOGUE_TEXT = (
    "INT. BEDROOM - NIGHT\n\n"
    "JACK\nI keep thinking about her face. The way she looked at me right before she left. Like she already knew.\n"
)


def _create_project_with_text(text: str, title_prefix: str) -> tuple[str, str]:
    # Create project
    r = requests.post(f"{API}/projects", json={"title": f"TEST_{title_prefix}_{int(time.time()*1000)}"})
    assert r.status_code in (200, 201), f"Create project failed: {r.status_code} {r.text}"
    pid = r.json()["id"]

    # Upload text via multipart form (matches /projects/{id}/documents endpoint)
    r2 = requests.post(
        f"{API}/projects/{pid}/documents",
        data={"pasted_text": text, "doc_type": "sides"},
    )
    assert r2.status_code in (200, 201), f"Upload text failed: {r2.status_code} {r2.text}"
    body = r2.json()
    doc_id = body.get("id") or body.get("document_id") or body.get("doc_id")
    if not doc_id and "document" in body:
        doc_id = body["document"].get("id")
    assert doc_id, f"No document id in response: {body}"

    # Confirm — pass cleaned_text = original text
    r3 = requests.post(
        f"{API}/documents/{doc_id}/confirm",
        json={"cleaned_text": text},
    )
    assert r3.status_code in (200, 201), f"Confirm doc failed: {r3.status_code} {r3.text}"
    return pid, doc_id


@pytest.fixture(scope="module")
def breakdown_pid():
    pid, _ = _create_project_with_text(BREAKDOWN_TEXT, "breakdown")
    return pid


@pytest.fixture(scope="module")
def script_pid():
    pid, _ = _create_project_with_text(SCRIPT_TEXT, "script")
    return pid


@pytest.fixture(scope="module")
def monologue_pid():
    pid, _ = _create_project_with_text(MONOLOGUE_TEXT, "monologue")
    return pid


# ------------------- DETECTION -------------------

class TestDetectContentType:
    def test_detect_breakdown(self, breakdown_pid):
        r = requests.post(f"{API}/projects/{breakdown_pid}/detect-content-type")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["content_type"] == "breakdown", f"Expected breakdown, got {data}"
        assert data["project_id"] == breakdown_pid

    def test_detect_script(self, script_pid):
        r = requests.post(f"{API}/projects/{script_pid}/detect-content-type")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["content_type"] == "script", f"Expected script, got {data}"

    def test_detect_monologue_is_breakdown(self, monologue_pid):
        # Single speaker monologue — only 1 unique speaker → breakdown
        r = requests.post(f"{API}/projects/{monologue_pid}/detect-content-type")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["content_type"] == "breakdown", f"Single-speaker monologue should be breakdown, got {data}"

    def test_detect_persists_on_project(self, breakdown_pid):
        # Re-fetch project, content_type should be stored
        r = requests.get(f"{API}/projects/{breakdown_pid}")
        assert r.status_code == 200
        proj = r.json()
        assert proj.get("content_type") == "breakdown"

    def test_detect_404_unknown_project(self):
        r = requests.post(f"{API}/projects/nonexistent-id-12345/detect-content-type")
        assert r.status_code == 404


# ------------------- EXTRACT-BREAKDOWN -------------------

class TestExtractBreakdown:
    def test_extract_returns_labeled_sections(self, breakdown_pid):
        r = requests.post(f"{API}/projects/{breakdown_pid}/extract-breakdown")
        assert r.status_code == 200, r.text
        data = r.json()
        sections = data.get("sections", [])
        assert len(sections) >= 3, f"Expected at least 3 sections, got {sections}"
        labels = [s["label"].upper() for s in sections]
        assert any("ROLE" in lbl for lbl in labels), f"ROLE missing in {labels}"
        assert any("CHARACTER" in lbl or "DESCRIPTION" in lbl for lbl in labels), f"CHARACTER DESCRIPTION missing in {labels}"
        assert any("CASTING" in lbl for lbl in labels), f"CASTING NOTES missing in {labels}"
        for s in sections:
            assert isinstance(s.get("content"), str) and len(s["content"]) > 0
        # full_text present
        assert "full_text" in data

    def test_extract_404(self):
        r = requests.post(f"{API}/projects/nonexistent-xyz/extract-breakdown")
        assert r.status_code == 404


# ------------------- QUICK COACH PROMPT SELECTION -------------------

class TestQuickCoachPromptRouting:
    def _set_character(self, pid, name):
        r = requests.put(f"{API}/projects/{pid}", json={"selected_character": name})
        assert r.status_code in (200, 201), f"Could not set selected_character: {r.status_code} {r.text}"
        return r.json()

    def test_breakdown_coach_runs_with_breakdown_prompt(self, breakdown_pid):
        # Ensure detect-content-type ran (stores content_type=breakdown)
        requests.post(f"{API}/projects/{breakdown_pid}/detect-content-type")
        self._set_character(breakdown_pid, "Jack Martinez")

        r2 = requests.post(
            f"{API}/projects/{breakdown_pid}/quick-coach",
            json={"force": True},
            timeout=90,
        )
        assert r2.status_code == 200, f"Coach failed: {r2.status_code} {r2.text}"
        data = r2.json()
        for key in ["casting_intent", "how_to_play_it", "what_to_avoid", "takes"]:
            assert key in data, f"Missing key {key} in coach response: {data}"
        assert isinstance(data["takes"], list) and len(data["takes"]) >= 1
        for t in data["takes"]:
            assert "label" in t and "direction" in t
        # Verify project content_type is still breakdown after coach call (sanity check)
        proj = requests.get(f"{API}/projects/{breakdown_pid}").json()
        assert proj.get("content_type") == "breakdown"
        # Verify cache was set
        assert proj.get("coach_cache") is not None

    def test_script_coach_runs_with_script_prompt(self, script_pid):
        # Detect content type first
        r0 = requests.post(f"{API}/projects/{script_pid}/detect-content-type")
        assert r0.json()["content_type"] == "script"

        self._set_character(script_pid, "SARAH")

        r2 = requests.post(
            f"{API}/projects/{script_pid}/quick-coach",
            json={"force": True},
            timeout=90,
        )
        assert r2.status_code == 200, f"Coach failed: {r2.status_code} {r2.text}"
        data = r2.json()
        for key in ["casting_intent", "how_to_play_it", "what_to_avoid", "takes"]:
            assert key in data
        proj = requests.get(f"{API}/projects/{script_pid}").json()
        assert proj.get("content_type") == "script"


# ------------------- UNIT-LEVEL DETECTION (via in-memory texts through project flow) -------------------

class TestDetectionEdgeCases:
    def test_all_caps_section_headers_not_confused_for_speakers(self):
        # Pure breakdown with ALL CAPS labels but no dialogue → should be breakdown
        text = (
            "ROLE\nDETECTIVE LANE\n\n"
            "DESCRIPTION\nMid 40s. Hardened by years on the force. Carries grief he does not share.\n\n"
            "CASTING NOTES\nGrounded. No theatrics.\n"
        )
        pid, _ = _create_project_with_text(text, "allcaps_headers")
        r = requests.post(f"{API}/projects/{pid}/detect-content-type")
        assert r.status_code == 200
        assert r.json()["content_type"] == "breakdown", f"ALL CAPS headers misread as speakers: {r.json()}"
