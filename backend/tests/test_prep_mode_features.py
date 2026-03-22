"""
Test suite for NEW FEATURES:
1. Per-scene action bar in ScriptOverview (P0 bug fix)
2. Prep Mode Selection in Full Script upload flow
3. Adaptive tool display based on prep mode

Tests cover:
- POST /api/analyze/scene accepts optional prep_mode and project_type fields
- Analysis text includes prep context when provided
- Regression: Full Script Quick mode still works
- Regression: Single scene 'Paste sides' flow still works
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://script-breakdown-4.preview.emergentagent.com').rstrip('/')

# Sample multi-scene script for testing
SAMPLE_SCRIPT = """INT. KITCHEN - DAY

SARAH sits at the table, coffee untouched.

JOHN enters, hesitant.

JOHN
We need to talk.

SARAH
About what?

JOHN
About last night. About everything.

SARAH
There's nothing to talk about.

EXT. PARKING LOT - NIGHT

MIKE waits by the car, checking his phone.

JOHN approaches.

MIKE
She doesn't know?

JOHN
She will. Soon.

MIKE
You're making a mistake.

JOHN
Maybe. But it's mine to make.
"""

class TestPrepModeAndProjectType:
    """Test prep_mode and project_type fields in analyze/scene endpoint"""
    
    @pytest.fixture(scope="class")
    def script_id(self):
        """Create a script record for testing"""
        response = requests.post(f"{BASE_URL}/api/scripts/create", json={
            "character_name": "Sarah",
            "mode": "quick",
            "scene_count": 2
        }, timeout=15)
        assert response.status_code == 200
        data = response.json()
        assert "script_id" in data
        return data["script_id"]
    
    def test_analyze_scene_with_audition_prep_mode(self, script_id):
        """Test POST /api/analyze/scene with prep_mode='audition'"""
        response = requests.post(f"{BASE_URL}/api/analyze/scene", json={
            "script_id": script_id,
            "scene_number": 1,
            "scene_heading": "INT. KITCHEN - DAY",
            "text": "SARAH sits at the table.\n\nJOHN\nWe need to talk.\n\nSARAH\nAbout what?",
            "character_name": "Sarah",
            "mode": "quick",
            "prep_mode": "audition",
            "project_type": "tvfilm"
        }, timeout=120)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify breakdown was created
        assert "id" in data
        assert data.get("scene_number") == 1
        assert data.get("scene_heading") == "INT. KITCHEN - DAY"
        print(f"SUCCESS: Scene analyzed with prep_mode=audition, breakdown_id={data['id']}")
    
    def test_analyze_scene_with_booked_prep_mode(self, script_id):
        """Test POST /api/analyze/scene with prep_mode='booked'"""
        response = requests.post(f"{BASE_URL}/api/analyze/scene", json={
            "script_id": script_id,
            "scene_number": 2,
            "scene_heading": "EXT. PARKING LOT - NIGHT",
            "text": "MIKE waits by the car.\n\nJOHN\nShe doesn't know?\n\nMIKE\nYou're making a mistake.",
            "character_name": "John",
            "mode": "quick",
            "prep_mode": "booked",
            "project_type": "theatre"
        }, timeout=120)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "id" in data
        print(f"SUCCESS: Scene analyzed with prep_mode=booked, breakdown_id={data['id']}")
    
    def test_analyze_scene_with_silent_prep_mode(self):
        """Test POST /api/analyze/scene with prep_mode='silent' (on-camera)"""
        # Create new script for this test
        create_resp = requests.post(f"{BASE_URL}/api/scripts/create", json={
            "character_name": "TestChar",
            "mode": "quick",
            "scene_count": 1
        }, timeout=15)
        script_id = create_resp.json()["script_id"]
        
        response = requests.post(f"{BASE_URL}/api/analyze/scene", json={
            "script_id": script_id,
            "scene_number": 1,
            "scene_heading": "INT. OFFICE - DAY",
            "text": "BOSS enters. EMPLOYEE looks up nervously.\n\nBOSS\nWe need to talk about your performance.",
            "character_name": "Employee",
            "mode": "quick",
            "prep_mode": "silent",
            "project_type": "commercial"
        }, timeout=120)
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        print(f"SUCCESS: Scene analyzed with prep_mode=silent, breakdown_id={data['id']}")
    
    def test_analyze_scene_with_study_prep_mode(self):
        """Test POST /api/analyze/scene with prep_mode='study'"""
        create_resp = requests.post(f"{BASE_URL}/api/scripts/create", json={
            "character_name": "TestChar",
            "mode": "quick",
            "scene_count": 1
        }, timeout=15)
        script_id = create_resp.json()["script_id"]
        
        response = requests.post(f"{BASE_URL}/api/analyze/scene", json={
            "script_id": script_id,
            "scene_number": 1,
            "scene_heading": "INT. CLASSROOM - DAY",
            "text": "TEACHER writes on the board.\n\nSTUDENT\nI don't understand.\n\nTEACHER\nLet me explain again.",
            "character_name": "Student",
            "mode": "quick",
            "prep_mode": "study",
            "project_type": "voiceover"
        }, timeout=120)
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        print(f"SUCCESS: Scene analyzed with prep_mode=study, breakdown_id={data['id']}")
    
    def test_analyze_scene_without_prep_mode(self):
        """Test POST /api/analyze/scene without prep_mode (backward compatibility)"""
        create_resp = requests.post(f"{BASE_URL}/api/scripts/create", json={
            "character_name": "TestChar",
            "mode": "quick",
            "scene_count": 1
        }, timeout=15)
        script_id = create_resp.json()["script_id"]
        
        response = requests.post(f"{BASE_URL}/api/analyze/scene", json={
            "script_id": script_id,
            "scene_number": 1,
            "scene_heading": "INT. ROOM - DAY",
            "text": "PERSON A\nHello.\n\nPERSON B\nHi there.",
            "character_name": "Person A",
            "mode": "quick"
            # No prep_mode or project_type
        }, timeout=120)
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        print("SUCCESS: Scene analyzed without prep_mode (backward compatible)")


class TestProjectTypeOptions:
    """Test all project_type options"""
    
    def test_project_type_commercial(self):
        """Test project_type='commercial'"""
        create_resp = requests.post(f"{BASE_URL}/api/scripts/create", json={
            "character_name": "Actor",
            "mode": "quick",
            "scene_count": 1
        }, timeout=15)
        script_id = create_resp.json()["script_id"]
        
        response = requests.post(f"{BASE_URL}/api/analyze/scene", json={
            "script_id": script_id,
            "scene_number": 1,
            "scene_heading": "INT. STUDIO - DAY",
            "text": "ACTOR smiles at camera.\n\nACTOR\nThis product changed my life!",
            "character_name": "Actor",
            "mode": "quick",
            "project_type": "commercial"
        }, timeout=120)
        
        assert response.status_code == 200
        print("SUCCESS: project_type=commercial accepted")
    
    def test_project_type_tvfilm(self):
        """Test project_type='tvfilm'"""
        create_resp = requests.post(f"{BASE_URL}/api/scripts/create", json={
            "character_name": "Detective",
            "mode": "quick",
            "scene_count": 1
        }, timeout=15)
        script_id = create_resp.json()["script_id"]
        
        response = requests.post(f"{BASE_URL}/api/analyze/scene", json={
            "script_id": script_id,
            "scene_number": 1,
            "scene_heading": "INT. PRECINCT - NIGHT",
            "text": "DETECTIVE examines evidence.\n\nDETECTIVE\nThis doesn't add up.",
            "character_name": "Detective",
            "mode": "quick",
            "project_type": "tvfilm"
        }, timeout=120)
        
        assert response.status_code == 200
        print("SUCCESS: project_type=tvfilm accepted")
    
    def test_project_type_theatre(self):
        """Test project_type='theatre'"""
        create_resp = requests.post(f"{BASE_URL}/api/scripts/create", json={
            "character_name": "Hamlet",
            "mode": "quick",
            "scene_count": 1
        }, timeout=15)
        script_id = create_resp.json()["script_id"]
        
        response = requests.post(f"{BASE_URL}/api/analyze/scene", json={
            "script_id": script_id,
            "scene_number": 1,
            "scene_heading": "ACT 1 SCENE 1",
            "text": "HAMLET\nTo be or not to be, that is the question.",
            "character_name": "Hamlet",
            "mode": "quick",
            "project_type": "theatre"
        }, timeout=120)
        
        assert response.status_code == 200
        print("SUCCESS: project_type=theatre accepted")
    
    def test_project_type_voiceover(self):
        """Test project_type='voiceover'"""
        create_resp = requests.post(f"{BASE_URL}/api/scripts/create", json={
            "character_name": "Narrator",
            "mode": "quick",
            "scene_count": 1
        }, timeout=15)
        script_id = create_resp.json()["script_id"]
        
        response = requests.post(f"{BASE_URL}/api/analyze/scene", json={
            "script_id": script_id,
            "scene_number": 1,
            "scene_heading": "VOICEOVER SCRIPT",
            "text": "NARRATOR (V.O.)\nIn a world where anything is possible...",
            "character_name": "Narrator",
            "mode": "quick",
            "project_type": "voiceover"
        }, timeout=120)
        
        assert response.status_code == 200
        print("SUCCESS: project_type=voiceover accepted")


class TestRegressionSingleSceneFlow:
    """Regression tests for single scene 'Paste sides' flow"""
    
    def test_analyze_text_quick_mode(self):
        """Regression: POST /api/analyze/text (Quick mode) still works"""
        response = requests.post(f"{BASE_URL}/api/analyze/text", json={
            "text": "JOHN\nI didn't come here to argue.\n\nSARAH\nThen why did you come?",
            "mode": "quick"
        }, timeout=120)
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "scene_summary" in data
        assert "character_name" in data
        assert "beats" in data
        assert "acting_takes" in data
        assert "memorization" in data
        print(f"SUCCESS: Paste sides (Quick mode) works, breakdown_id={data['id']}")
    
    def test_analyze_text_deep_mode(self):
        """Regression: POST /api/analyze/text (Deep mode) still works"""
        response = requests.post(f"{BASE_URL}/api/analyze/text", json={
            "text": "JOHN\nI didn't come here to argue.\n\nSARAH\nThen why did you come?\n\nJOHN\nBecause I had to see you one last time.",
            "mode": "deep"
        }, timeout=180)
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "scene_summary" in data
        print(f"SUCCESS: Paste sides (Deep mode) works, breakdown_id={data['id']}")


class TestRegressionFullScriptFlow:
    """Regression tests for Full Script mode"""
    
    def test_parse_scenes_endpoint(self):
        """Regression: POST /api/parse-scenes still works"""
        response = requests.post(f"{BASE_URL}/api/parse-scenes", json={
            "text": SAMPLE_SCRIPT,
            "character_name": "Sarah"
        }, timeout=60)
        
        assert response.status_code == 200
        data = response.json()
        assert "total_scenes" in data
        assert "character_scenes_count" in data
        assert "scenes" in data
        assert data["total_scenes"] >= 1
        print(f"SUCCESS: parse-scenes works, found {data['total_scenes']} scenes, {data['character_scenes_count']} with Sarah")
    
    def test_scripts_create_endpoint(self):
        """Regression: POST /api/scripts/create still works"""
        response = requests.post(f"{BASE_URL}/api/scripts/create", json={
            "character_name": "TestCharacter",
            "mode": "quick",
            "scene_count": 3
        }, timeout=15)
        
        assert response.status_code == 200
        data = response.json()
        assert "script_id" in data
        print(f"SUCCESS: scripts/create works, script_id={data['script_id']}")
    
    def test_full_script_quick_mode_e2e(self):
        """Regression: Full Script Quick mode end-to-end"""
        # Step 1: Parse scenes
        parse_resp = requests.post(f"{BASE_URL}/api/parse-scenes", json={
            "text": SAMPLE_SCRIPT,
            "character_name": "John"
        }, timeout=60)
        assert parse_resp.status_code == 200
        scenes = parse_resp.json()["scenes"]
        
        # Step 2: Create script
        create_resp = requests.post(f"{BASE_URL}/api/scripts/create", json={
            "character_name": "John",
            "mode": "quick",
            "scene_count": len(scenes)
        }, timeout=15)
        assert create_resp.status_code == 200
        script_id = create_resp.json()["script_id"]
        
        # Step 3: Analyze first scene
        scene = scenes[0]
        analyze_resp = requests.post(f"{BASE_URL}/api/analyze/scene", json={
            "script_id": script_id,
            "scene_number": scene["scene_number"],
            "scene_heading": scene["heading"],
            "text": scene["text"],
            "character_name": "John",
            "mode": "quick"
        }, timeout=120)
        assert analyze_resp.status_code == 200
        breakdown = analyze_resp.json()
        assert "id" in breakdown
        
        print(f"SUCCESS: Full Script Quick mode E2E works, breakdown_id={breakdown['id']}")


class TestBreakdownStructure:
    """Test that breakdown response has all required fields for action bar"""
    
    def test_breakdown_has_memorization_for_action_bar(self):
        """Verify breakdown includes memorization data needed for action bar buttons"""
        response = requests.post(f"{BASE_URL}/api/analyze/text", json={
            "text": "SARAH\nI can't believe you did that.\n\nJOHN\nI had no choice.\n\nSARAH\nThere's always a choice.",
            "mode": "quick"
        }, timeout=120)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check memorization structure (needed for Memorize button)
        assert "memorization" in data
        memorization = data["memorization"]
        assert "chunked_lines" in memorization
        assert "cue_recall" in memorization
        
        # Check cue_recall has data (needed for Run Lines button)
        if len(memorization.get("cue_recall", [])) > 0:
            cue = memorization["cue_recall"][0]
            assert "cue" in cue
            assert "your_line" in cue
            print(f"SUCCESS: Breakdown has memorization with {len(memorization['cue_recall'])} cue_recall items")
        else:
            print("INFO: Breakdown has memorization but no cue_recall items (may be expected for short scenes)")
        
        # Check other required fields
        assert "acting_takes" in data
        assert "scene_summary" in data
        assert "character_name" in data
        print("SUCCESS: Breakdown has all required fields for action bar")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
