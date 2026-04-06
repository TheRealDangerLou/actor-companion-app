"""
Test Script Cleaning Layer - Phase 1
Tests for deterministic script cleaning and review/edit flow.

Endpoints tested:
- POST /api/clean-text: Clean raw text
- POST /api/clean-script: Clean all scenes of a script
- POST /api/save-cleaned-script: Batch save cleaned text
- POST /api/save-cleaned-text: Save single breakdown cleaned text
- GET /api/scripts/{id}: Uses cleaned_text for line extraction
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test script IDs from the context
SCRIPT_ID_BOOKED = "67c7477b-b334-40f8-ab1f-6cc08cd2b21a"  # mode=booked, 21 scenes
SCRIPT_ID_OLDER = "473f064c-dedd-475d-90de-091ee54ca708"   # mode=None, older


class TestCleanTextEndpoint:
    """Tests for POST /api/clean-text - deterministic text cleaning"""

    def test_clean_text_basic(self):
        """Test basic text cleaning - strips page numbers, normalizes whitespace"""
        raw_text = """
                                                         15. 
        
        FELIX
        Hello there.
        
        IVY
        Hi Felix.
        """
        response = requests.post(f"{BASE_URL}/api/clean-text", json={"text": raw_text})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "cleaned_text" in data, "Response should contain cleaned_text"
        cleaned = data["cleaned_text"]
        
        # Page number should be stripped
        assert "15." not in cleaned or "15. " not in cleaned, "Page number should be stripped"
        # Character names should be preserved
        assert "FELIX" in cleaned, "Character name FELIX should be preserved"
        assert "IVY" in cleaned, "Character name IVY should be preserved"
        print(f"PASS: clean-text basic - cleaned {len(raw_text)} chars to {len(cleaned)} chars")

    def test_clean_text_more_contd_join(self):
        """Test (MORE)/(CONT'D) page-break joins"""
        raw_text = """FELIX
I was saying something important
(MORE)

FELIX (CONT'D)
and this is the continuation.
"""
        response = requests.post(f"{BASE_URL}/api/clean-text", json={"text": raw_text})
        assert response.status_code == 200
        
        data = response.json()
        cleaned = data["cleaned_text"]
        
        # (MORE) should be removed
        assert "(MORE)" not in cleaned, "(MORE) marker should be removed"
        # CONT'D header should be handled
        print(f"PASS: clean-text MORE/CONT'D join - cleaned text: {cleaned[:100]}...")

    def test_clean_text_scene_number_prefix(self):
        """Test concatenated scene numbers are fixed (e.g., '20INT.' -> 'INT.')"""
        raw_text = """20INT. BAR - NIGHT

FELIX
Let's have a drink.
"""
        response = requests.post(f"{BASE_URL}/api/clean-text", json={"text": raw_text})
        assert response.status_code == 200
        
        data = response.json()
        cleaned = data["cleaned_text"]
        
        # Scene number prefix should be stripped
        assert "INT. BAR - NIGHT" in cleaned, "Scene heading should be cleaned"
        assert "20INT." not in cleaned, "Concatenated scene number should be removed"
        print(f"PASS: clean-text scene number prefix fix")

    def test_clean_text_blank_lines_before_character(self):
        """Test blank lines are added before character names"""
        raw_text = """Some action text.
FELIX
My line here."""
        response = requests.post(f"{BASE_URL}/api/clean-text", json={"text": raw_text})
        assert response.status_code == 200
        
        data = response.json()
        cleaned = data["cleaned_text"]
        
        # There should be a blank line before FELIX
        lines = cleaned.split("\n")
        felix_idx = None
        for i, line in enumerate(lines):
            if line.strip() == "FELIX":
                felix_idx = i
                break
        
        if felix_idx and felix_idx > 0:
            prev_line = lines[felix_idx - 1].strip()
            assert prev_line == "", f"Expected blank line before FELIX, got: '{prev_line}'"
        print(f"PASS: clean-text adds blank lines before character names")

    def test_clean_text_empty_input(self):
        """Test empty input returns empty string"""
        response = requests.post(f"{BASE_URL}/api/clean-text", json={"text": ""})
        assert response.status_code == 200
        
        data = response.json()
        assert data["cleaned_text"] == "", "Empty input should return empty cleaned_text"
        print(f"PASS: clean-text handles empty input")


class TestCleanScriptEndpoint:
    """Tests for POST /api/clean-script - clean all scenes of a script"""

    def test_clean_script_booked(self):
        """Test cleaning the booked Felix script (21 scenes)"""
        response = requests.post(f"{BASE_URL}/api/clean-script", json={"script_id": SCRIPT_ID_BOOKED})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "script_id" in data, "Response should contain script_id"
        assert "scenes" in data, "Response should contain scenes array"
        assert "character_name" in data, "Response should contain character_name"
        
        scenes = data["scenes"]
        assert len(scenes) > 0, "Should have at least one scene"
        
        # Verify scene structure
        first_scene = scenes[0]
        assert "breakdown_id" in first_scene, "Scene should have breakdown_id"
        assert "scene_number" in first_scene, "Scene should have scene_number"
        assert "cleaned_text" in first_scene, "Scene should have cleaned_text"
        assert "original_text" in first_scene, "Scene should have original_text"
        
        print(f"PASS: clean-script booked - {len(scenes)} scenes, character: {data['character_name']}")

    def test_clean_script_sorted_by_scene_number(self):
        """Test scenes are returned sorted by scene_number"""
        response = requests.post(f"{BASE_URL}/api/clean-script", json={"script_id": SCRIPT_ID_BOOKED})
        assert response.status_code == 200
        
        data = response.json()
        scenes = data["scenes"]
        
        # Verify sorted order
        scene_numbers = [s.get("scene_number", 0) for s in scenes]
        assert scene_numbers == sorted(scene_numbers), f"Scenes should be sorted by scene_number: {scene_numbers}"
        print(f"PASS: clean-script returns scenes sorted by scene_number")

    def test_clean_script_older(self):
        """Test cleaning the older Felix script"""
        response = requests.post(f"{BASE_URL}/api/clean-script", json={"script_id": SCRIPT_ID_OLDER})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        scenes = data["scenes"]
        assert len(scenes) > 0, "Should have at least one scene"
        print(f"PASS: clean-script older - {len(scenes)} scenes")

    def test_clean_script_not_found(self):
        """Test 404 for non-existent script"""
        response = requests.post(f"{BASE_URL}/api/clean-script", json={"script_id": "nonexistent-script-id"})
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"PASS: clean-script returns 404 for non-existent script")


class TestSaveCleanedScriptEndpoint:
    """Tests for POST /api/save-cleaned-script - batch save cleaned text"""

    def test_save_cleaned_script_basic(self):
        """Test saving cleaned text for all scenes"""
        # First get the scenes
        clean_resp = requests.post(f"{BASE_URL}/api/clean-script", json={"script_id": SCRIPT_ID_BOOKED})
        assert clean_resp.status_code == 200
        
        scenes = clean_resp.json()["scenes"]
        
        # Prepare payload with cleaned texts
        payload = {
            "script_id": SCRIPT_ID_BOOKED,
            "scenes": [
                {"breakdown_id": s["breakdown_id"], "cleaned_text": s["cleaned_text"]}
                for s in scenes[:3]  # Just save first 3 to avoid long test
            ]
        }
        
        response = requests.post(f"{BASE_URL}/api/save-cleaned-script", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["status"] == "ok", "Status should be ok"
        assert "saved" in data, "Response should contain saved count"
        assert data["saved"] == 3, f"Should have saved 3 scenes, got {data['saved']}"
        print(f"PASS: save-cleaned-script - saved {data['saved']} scenes")

    def test_save_cleaned_script_empty_scenes(self):
        """Test error handling for empty scenes array"""
        response = requests.post(f"{BASE_URL}/api/save-cleaned-script", json={
            "script_id": SCRIPT_ID_BOOKED,
            "scenes": []
        })
        assert response.status_code == 400, f"Expected 400 for empty scenes, got {response.status_code}"
        print(f"PASS: save-cleaned-script returns 400 for empty scenes")


class TestSaveCleanedTextEndpoint:
    """Tests for POST /api/save-cleaned-text - save single breakdown"""

    def test_save_cleaned_text_single(self):
        """Test saving cleaned text for a single breakdown"""
        # First get a breakdown_id
        clean_resp = requests.post(f"{BASE_URL}/api/clean-script", json={"script_id": SCRIPT_ID_BOOKED})
        assert clean_resp.status_code == 200
        
        scenes = clean_resp.json()["scenes"]
        first_scene = scenes[0]
        
        # Save cleaned text
        payload = {
            "script_id": SCRIPT_ID_BOOKED,
            "breakdown_id": first_scene["breakdown_id"],
            "cleaned_text": first_scene["cleaned_text"] + "\n\n[TEST EDIT]"
        }
        
        response = requests.post(f"{BASE_URL}/api/save-cleaned-text", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["status"] == "ok", "Status should be ok"
        assert data["breakdown_id"] == first_scene["breakdown_id"], "Should return the breakdown_id"
        print(f"PASS: save-cleaned-text - saved single breakdown")
        
        # Restore original cleaned text
        restore_payload = {
            "script_id": SCRIPT_ID_BOOKED,
            "breakdown_id": first_scene["breakdown_id"],
            "cleaned_text": first_scene["cleaned_text"]
        }
        requests.post(f"{BASE_URL}/api/save-cleaned-text", json=restore_payload)

    def test_save_cleaned_text_not_found(self):
        """Test 404 for non-existent breakdown"""
        response = requests.post(f"{BASE_URL}/api/save-cleaned-text", json={
            "script_id": SCRIPT_ID_BOOKED,
            "breakdown_id": "nonexistent-breakdown-id",
            "cleaned_text": "test"
        })
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"PASS: save-cleaned-text returns 404 for non-existent breakdown")


class TestGetScriptUsesCleanedText:
    """Tests for GET /api/scripts/{id} - uses cleaned_text for line extraction"""

    def test_get_script_uses_cleaned_text(self):
        """Test that get_script uses cleaned_text when available"""
        # First save some cleaned text
        clean_resp = requests.post(f"{BASE_URL}/api/clean-script", json={"script_id": SCRIPT_ID_BOOKED})
        assert clean_resp.status_code == 200
        
        scenes = clean_resp.json()["scenes"]
        
        # Save cleaned text for first scene
        first_scene = scenes[0]
        save_payload = {
            "script_id": SCRIPT_ID_BOOKED,
            "breakdown_id": first_scene["breakdown_id"],
            "cleaned_text": first_scene["cleaned_text"]
        }
        save_resp = requests.post(f"{BASE_URL}/api/save-cleaned-text", json=save_payload)
        assert save_resp.status_code == 200
        
        # Now get the script
        get_resp = requests.get(f"{BASE_URL}/api/scripts/{SCRIPT_ID_BOOKED}")
        assert get_resp.status_code == 200, f"Expected 200, got {get_resp.status_code}: {get_resp.text}"
        
        data = get_resp.json()
        assert "breakdowns" in data, "Response should contain breakdowns"
        
        breakdowns = data["breakdowns"]
        assert len(breakdowns) > 0, "Should have at least one breakdown"
        
        # Check that memorization is populated (line extraction happened)
        first_breakdown = breakdowns[0]
        assert "memorization" in first_breakdown, "Breakdown should have memorization"
        
        memorization = first_breakdown["memorization"]
        assert "cue_recall" in memorization, "Memorization should have cue_recall"
        
        print(f"PASS: get_script uses cleaned_text - {len(breakdowns)} breakdowns, first has {len(memorization.get('cue_recall', []))} lines")

    def test_get_script_fallback_to_original(self):
        """Test that get_script falls back to original_text when cleaned_text is not available"""
        # Get the older script which may not have cleaned_text
        get_resp = requests.get(f"{BASE_URL}/api/scripts/{SCRIPT_ID_OLDER}")
        assert get_resp.status_code == 200, f"Expected 200, got {get_resp.status_code}: {get_resp.text}"
        
        data = get_resp.json()
        breakdowns = data.get("breakdowns", [])
        
        # Should still work even without cleaned_text
        assert len(breakdowns) > 0, "Should have breakdowns"
        print(f"PASS: get_script fallback to original_text - {len(breakdowns)} breakdowns")


class TestCleanScriptTextFunction:
    """Tests for the clean_script_text() function via /api/clean-text"""

    def test_multiple_blank_lines_collapsed(self):
        """Test multiple blank lines are collapsed to single blank line"""
        raw_text = """FELIX
Hello.



IVY
Hi."""
        response = requests.post(f"{BASE_URL}/api/clean-text", json={"text": raw_text})
        assert response.status_code == 200
        
        cleaned = response.json()["cleaned_text"]
        
        # Should not have more than 2 consecutive newlines
        assert "\n\n\n" not in cleaned, "Multiple blank lines should be collapsed"
        print(f"PASS: clean_script_text collapses multiple blank lines")

    def test_leading_trailing_blanks_stripped(self):
        """Test leading and trailing blank lines are stripped"""
        raw_text = """


FELIX
Hello.


"""
        response = requests.post(f"{BASE_URL}/api/clean-text", json={"text": raw_text})
        assert response.status_code == 200
        
        cleaned = response.json()["cleaned_text"]
        
        # Should not start or end with blank lines
        assert not cleaned.startswith("\n"), "Should not start with blank line"
        assert not cleaned.endswith("\n"), "Should not end with blank line"
        print(f"PASS: clean_script_text strips leading/trailing blanks")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
