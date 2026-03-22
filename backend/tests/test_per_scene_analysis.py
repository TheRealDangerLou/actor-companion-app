"""
Test suite for Bug Fix: Per-Scene Analysis to avoid 502 Gateway Timeout
Tests the new endpoints:
- POST /api/scripts/create - Initialize script record
- POST /api/analyze/scene - Analyze single scene
- GET /api/scripts/{script_id} - Get script with linked breakdowns
Also tests regression for existing endpoints.
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Sample multi-scene script for testing
SAMPLE_SCRIPT = """
INT. COFFEE SHOP - DAY

SARAH sits alone at a table, staring at her phone. JOHN enters.

JOHN
Hey. You wanted to talk?

SARAH
Sit down.

JOHN
(sitting)
This feels serious.

SARAH
It is. I know about the money, John.

JOHN
What money?

SARAH
Don't. Just don't.

INT. SARAH'S APARTMENT - NIGHT

SARAH paces. Her phone rings. She answers.

SARAH
What do you want?

JOHN (V.O.)
I can explain everything.

SARAH
You had your chance.

She hangs up.
"""

SINGLE_SCENE_TEXT = """
INT. OFFICE - DAY

MARK sits at his desk. LISA enters.

LISA
We need to talk about the project.

MARK
What about it?

LISA
It's behind schedule. Way behind.

MARK
I'm aware.

LISA
Then do something about it.
"""


class TestScriptsCreateEndpoint:
    """Tests for POST /api/scripts/create"""
    
    def test_create_script_returns_script_id(self):
        """POST /api/scripts/create should return a script_id"""
        response = requests.post(
            f"{BASE_URL}/api/scripts/create",
            json={
                "character_name": "TEST_Sarah",
                "mode": "quick",
                "scene_count": 2
            },
            timeout=15
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "script_id" in data, "Response should contain script_id"
        assert isinstance(data["script_id"], str), "script_id should be a string"
        assert len(data["script_id"]) > 0, "script_id should not be empty"
        print(f"✓ Created script with ID: {data['script_id']}")
    
    def test_create_script_with_deep_mode(self):
        """POST /api/scripts/create with mode=deep should work"""
        response = requests.post(
            f"{BASE_URL}/api/scripts/create",
            json={
                "character_name": "TEST_John",
                "mode": "deep",
                "scene_count": 3
            },
            timeout=15
        )
        assert response.status_code == 200
        data = response.json()
        assert "script_id" in data
        print(f"✓ Created deep mode script with ID: {data['script_id']}")


class TestAnalyzeSceneEndpoint:
    """Tests for POST /api/analyze/scene"""
    
    def test_analyze_single_scene_quick_mode(self):
        """POST /api/analyze/scene with mode=quick should complete within timeout"""
        # First create a script
        create_resp = requests.post(
            f"{BASE_URL}/api/scripts/create",
            json={"character_name": "TEST_Lisa", "mode": "quick", "scene_count": 1},
            timeout=15
        )
        assert create_resp.status_code == 200
        script_id = create_resp.json()["script_id"]
        
        # Now analyze a single scene
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/api/analyze/scene",
            json={
                "script_id": script_id,
                "scene_number": 1,
                "scene_heading": "INT. OFFICE - DAY",
                "text": SINGLE_SCENE_TEXT,
                "character_name": "Lisa",
                "mode": "quick"
            },
            timeout=120
        )
        elapsed = time.time() - start_time
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify breakdown structure
        assert "id" in data, "Response should contain breakdown id"
        assert "script_id" in data, "Response should contain script_id"
        assert data["script_id"] == script_id, "script_id should match"
        assert "scene_number" in data, "Response should contain scene_number"
        assert "scene_summary" in data, "Response should contain scene_summary"
        assert "character_name" in data, "Response should contain character_name"
        assert "beats" in data, "Response should contain beats"
        
        print(f"✓ Quick mode scene analysis completed in {elapsed:.1f}s")
        print(f"  Breakdown ID: {data['id']}")
        print(f"  Character: {data.get('character_name', 'N/A')}")
    
    def test_analyze_single_scene_deep_mode_within_timeout(self):
        """POST /api/analyze/scene with mode=deep should complete within 120s"""
        # Create script
        create_resp = requests.post(
            f"{BASE_URL}/api/scripts/create",
            json={"character_name": "TEST_Mark", "mode": "deep", "scene_count": 1},
            timeout=15
        )
        assert create_resp.status_code == 200
        script_id = create_resp.json()["script_id"]
        
        # Analyze scene in deep mode
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/api/analyze/scene",
            json={
                "script_id": script_id,
                "scene_number": 1,
                "scene_heading": "INT. OFFICE - DAY",
                "text": SINGLE_SCENE_TEXT,
                "character_name": "Mark",
                "mode": "deep"
            },
            timeout=180  # 3 min max
        )
        elapsed = time.time() - start_time
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert elapsed < 120, f"Deep mode should complete within 120s, took {elapsed:.1f}s"
        
        data = response.json()
        assert "id" in data
        assert "scene_summary" in data
        
        print(f"✓ Deep mode scene analysis completed in {elapsed:.1f}s (under 120s limit)")
    
    def test_analyze_scene_empty_text_returns_400(self):
        """POST /api/analyze/scene with empty text should return 400"""
        create_resp = requests.post(
            f"{BASE_URL}/api/scripts/create",
            json={"character_name": "TEST_Empty", "mode": "quick", "scene_count": 1},
            timeout=15
        )
        script_id = create_resp.json()["script_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/analyze/scene",
            json={
                "script_id": script_id,
                "scene_number": 1,
                "scene_heading": "INT. TEST",
                "text": "",
                "character_name": "Test",
                "mode": "quick"
            },
            timeout=15
        )
        assert response.status_code == 400, f"Expected 400 for empty text, got {response.status_code}"
        print("✓ Empty text correctly returns 400")


class TestGetScriptEndpoint:
    """Tests for GET /api/scripts/{script_id}"""
    
    def test_get_script_with_breakdowns(self):
        """GET /api/scripts/{script_id} should return script with linked breakdowns"""
        # Create script
        create_resp = requests.post(
            f"{BASE_URL}/api/scripts/create",
            json={"character_name": "TEST_GetScript", "mode": "quick", "scene_count": 2},
            timeout=15
        )
        assert create_resp.status_code == 200
        script_id = create_resp.json()["script_id"]
        
        # Analyze two scenes
        for i in range(1, 3):
            resp = requests.post(
                f"{BASE_URL}/api/analyze/scene",
                json={
                    "script_id": script_id,
                    "scene_number": i,
                    "scene_heading": f"INT. SCENE {i}",
                    "text": f"CHAR\nLine {i}.\nOTHER\nResponse {i}.",
                    "character_name": "Char",
                    "mode": "quick"
                },
                timeout=120
            )
            assert resp.status_code == 200, f"Scene {i} analysis failed"
        
        # Get script with breakdowns
        get_resp = requests.get(f"{BASE_URL}/api/scripts/{script_id}", timeout=15)
        assert get_resp.status_code == 200, f"Expected 200, got {get_resp.status_code}"
        
        data = get_resp.json()
        assert "id" in data, "Script should have id"
        assert data["id"] == script_id, "Script id should match"
        assert "breakdowns" in data, "Script should have breakdowns array"
        assert len(data["breakdowns"]) == 2, f"Expected 2 breakdowns, got {len(data['breakdowns'])}"
        assert "character_name" in data, "Script should have character_name"
        
        print(f"✓ GET /api/scripts/{script_id} returned script with {len(data['breakdowns'])} breakdowns")
    
    def test_get_nonexistent_script_returns_404(self):
        """GET /api/scripts/{invalid_id} should return 404"""
        response = requests.get(f"{BASE_URL}/api/scripts/nonexistent-id-12345", timeout=15)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Nonexistent script correctly returns 404")


class TestRegressionSingleSceneAnalysis:
    """Regression tests for single scene analysis (Paste sides flow)"""
    
    def test_analyze_text_quick_mode_still_works(self):
        """POST /api/analyze/text (Quick mode) should still work"""
        response = requests.post(
            f"{BASE_URL}/api/analyze/text",
            json={
                "text": SINGLE_SCENE_TEXT,
                "mode": "quick"
            },
            timeout=120
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "id" in data
        assert "scene_summary" in data
        assert "beats" in data
        print("✓ Regression: POST /api/analyze/text (Quick mode) works")
    
    def test_analyze_text_deep_mode_still_works(self):
        """POST /api/analyze/text (Deep mode) should still work"""
        response = requests.post(
            f"{BASE_URL}/api/analyze/text",
            json={
                "text": SINGLE_SCENE_TEXT,
                "mode": "deep"
            },
            timeout=180
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "id" in data
        assert "scene_summary" in data
        print("✓ Regression: POST /api/analyze/text (Deep mode) works")


class TestRegressionFullScriptQuickMode:
    """Regression tests for Full Script Quick mode (batch endpoint)"""
    
    def test_parse_scenes_still_works(self):
        """POST /api/parse-scenes should still work"""
        response = requests.post(
            f"{BASE_URL}/api/parse-scenes",
            json={
                "text": SAMPLE_SCRIPT,
                "character_name": "Sarah"
            },
            timeout=60
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "scenes" in data
        assert "total_scenes" in data
        assert data["total_scenes"] >= 2, "Should find at least 2 scenes"
        print(f"✓ Regression: POST /api/parse-scenes found {data['total_scenes']} scenes")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
