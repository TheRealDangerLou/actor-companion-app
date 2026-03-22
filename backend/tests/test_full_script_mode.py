"""
Test Full Script Mode - Scene Parsing and Batch Analysis
Tests the new endpoints: /api/parse-scenes, /api/analyze/batch, /api/scripts/{script_id}
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Sample multi-scene script for testing
SAMPLE_SCRIPT = """INT. KITCHEN - DAY

SARAH sits at the table. JOHN enters.

JOHN
We need to talk.

SARAH
About what?

JOHN
You know about what.

SARAH
I really dont.

EXT. PARKING LOT - NIGHT

JOHN walks to his car. MIKE is leaning against it.

MIKE
She doesnt know, does she?

JOHN
She will soon enough.

MIKE
You sure about this?

INT. SARAHS APARTMENT - LATER

SARAH opens her laptop. A notification appears.

SARAH
(to herself)
No. No, no, no.

She grabs her keys and runs out."""

# Script without standard headers (should trigger GPT fallback)
SCRIPT_NO_HEADERS = """The kitchen is quiet. Sarah sits alone.

SARAH
I can't believe he's gone.

She stares at the empty chair across from her.

Later, in the parking lot.

JOHN
I had to leave. You understand.

SARAH
No. I don't understand anything anymore.

They stand in silence."""


class TestParseScenes:
    """Tests for POST /api/parse-scenes endpoint"""
    
    def test_parse_scenes_with_standard_headers(self):
        """Test scene parsing with INT./EXT. headers - should use regex"""
        response = requests.post(
            f"{BASE_URL}/api/parse-scenes",
            json={
                "text": SAMPLE_SCRIPT,
                "character_name": "Sarah"
            },
            timeout=60
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "total_scenes" in data
        assert "character_scenes_count" in data
        assert "character_name" in data
        assert "scenes" in data
        
        # Should find 3 scenes
        assert data["total_scenes"] == 3, f"Expected 3 scenes, got {data['total_scenes']}"
        
        # Sarah appears in 2 scenes (Kitchen and Apartment)
        assert data["character_scenes_count"] == 2, f"Expected 2 Sarah scenes, got {data['character_scenes_count']}"
        
        # Verify character name is preserved
        assert data["character_name"] == "Sarah"
        
        # Verify scene structure
        for scene in data["scenes"]:
            assert "scene_number" in scene
            assert "heading" in scene
            assert "preview" in scene
            assert "characters" in scene
            assert "text" in scene
            assert "has_character" in scene
            assert isinstance(scene["characters"], list)
        
        # Verify specific scenes
        scene_headings = [s["heading"] for s in data["scenes"]]
        assert any("KITCHEN" in h.upper() for h in scene_headings), "Kitchen scene not found"
        assert any("PARKING" in h.upper() for h in scene_headings), "Parking lot scene not found"
        assert any("APARTMENT" in h.upper() for h in scene_headings), "Apartment scene not found"
        
        print(f"✓ Parsed {data['total_scenes']} scenes, {data['character_scenes_count']} with Sarah")
    
    def test_parse_scenes_character_detection(self):
        """Test that characters are correctly detected in each scene"""
        response = requests.post(
            f"{BASE_URL}/api/parse-scenes",
            json={
                "text": SAMPLE_SCRIPT,
                "character_name": "John"
            },
            timeout=60
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # John appears in Kitchen and Parking Lot (2 scenes)
        assert data["character_scenes_count"] == 2, f"Expected 2 John scenes, got {data['character_scenes_count']}"
        
        # Verify has_character flag
        john_scenes = [s for s in data["scenes"] if s["has_character"]]
        assert len(john_scenes) == 2
        
        print(f"✓ John correctly detected in {len(john_scenes)} scenes")
    
    def test_parse_scenes_mike_only_in_parking(self):
        """Test that Mike only appears in parking lot scene"""
        response = requests.post(
            f"{BASE_URL}/api/parse-scenes",
            json={
                "text": SAMPLE_SCRIPT,
                "character_name": "Mike"
            },
            timeout=60
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Mike only appears in 1 scene (Parking Lot)
        assert data["character_scenes_count"] == 1, f"Expected 1 Mike scene, got {data['character_scenes_count']}"
        
        mike_scene = [s for s in data["scenes"] if s["has_character"]][0]
        assert "PARKING" in mike_scene["heading"].upper()
        
        print(f"✓ Mike correctly detected only in parking lot scene")
    
    def test_parse_scenes_empty_text_error(self):
        """Test that empty text returns 400 error"""
        response = requests.post(
            f"{BASE_URL}/api/parse-scenes",
            json={
                "text": "",
                "character_name": "Sarah"
            },
            timeout=30
        )
        
        assert response.status_code == 400
        assert "empty" in response.json().get("detail", "").lower()
        print("✓ Empty text correctly rejected with 400")
    
    def test_parse_scenes_empty_character_error(self):
        """Test that empty character name returns 400 error"""
        response = requests.post(
            f"{BASE_URL}/api/parse-scenes",
            json={
                "text": SAMPLE_SCRIPT,
                "character_name": ""
            },
            timeout=30
        )
        
        assert response.status_code == 400
        assert "character" in response.json().get("detail", "").lower()
        print("✓ Empty character name correctly rejected with 400")
    
    def test_parse_scenes_gpt_fallback(self):
        """Test that scripts without INT./EXT. headers use GPT fallback"""
        response = requests.post(
            f"{BASE_URL}/api/parse-scenes",
            json={
                "text": SCRIPT_NO_HEADERS,
                "character_name": "Sarah"
            },
            timeout=90  # GPT fallback takes longer
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should still find scenes (GPT will split it)
        assert data["total_scenes"] >= 1, "GPT should find at least 1 scene"
        assert "scenes" in data
        
        print(f"✓ GPT fallback found {data['total_scenes']} scenes")


class TestBatchAnalyze:
    """Tests for POST /api/analyze/batch endpoint"""
    
    @pytest.fixture
    def parsed_scenes(self):
        """Get parsed scenes for batch analysis"""
        response = requests.post(
            f"{BASE_URL}/api/parse-scenes",
            json={
                "text": SAMPLE_SCRIPT,
                "character_name": "Sarah"
            },
            timeout=60
        )
        return response.json()
    
    def test_batch_analyze_single_scene(self, parsed_scenes):
        """Test batch analysis with a single scene"""
        sarah_scenes = [s for s in parsed_scenes["scenes"] if s["has_character"]]
        assert len(sarah_scenes) >= 1
        
        # Analyze just the first Sarah scene
        scene_to_analyze = sarah_scenes[0]
        
        response = requests.post(
            f"{BASE_URL}/api/analyze/batch",
            json={
                "scenes": [{
                    "scene_number": scene_to_analyze["scene_number"],
                    "text": scene_to_analyze["text"],
                    "heading": scene_to_analyze["heading"]
                }],
                "character_name": "Sarah",
                "mode": "quick"
            },
            timeout=120
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "script_id" in data
        assert "character_name" in data
        assert "mode" in data
        assert "breakdowns" in data
        
        assert data["character_name"] == "Sarah"
        assert data["mode"] == "quick"
        assert len(data["breakdowns"]) == 1
        
        # Verify breakdown structure
        breakdown = data["breakdowns"][0]
        assert "id" in breakdown
        assert "script_id" in breakdown
        assert breakdown["script_id"] == data["script_id"]
        assert "scene_number" in breakdown
        assert "scene_heading" in breakdown
        assert "scene_summary" in breakdown
        assert "character_objective" in breakdown
        assert "beats" in breakdown
        assert "acting_takes" in breakdown
        
        print(f"✓ Single scene batch analysis successful, script_id: {data['script_id']}")
        return data["script_id"]
    
    def test_batch_analyze_multiple_scenes(self, parsed_scenes):
        """Test batch analysis with multiple scenes (Quick mode)"""
        sarah_scenes = [s for s in parsed_scenes["scenes"] if s["has_character"]]
        assert len(sarah_scenes) >= 2, "Need at least 2 Sarah scenes for this test"
        
        # Analyze both Sarah scenes
        scenes_to_analyze = [{
            "scene_number": s["scene_number"],
            "text": s["text"],
            "heading": s["heading"]
        } for s in sarah_scenes]
        
        response = requests.post(
            f"{BASE_URL}/api/analyze/batch",
            json={
                "scenes": scenes_to_analyze,
                "character_name": "Sarah",
                "mode": "quick"
            },
            timeout=180  # 2 scenes * ~90s each
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Should have 2 breakdowns
        assert len(data["breakdowns"]) == 2, f"Expected 2 breakdowns, got {len(data['breakdowns'])}"
        
        # All breakdowns should share the same script_id
        script_id = data["script_id"]
        for b in data["breakdowns"]:
            assert b["script_id"] == script_id
        
        # Verify scene numbers are preserved
        scene_numbers = [b["scene_number"] for b in data["breakdowns"]]
        expected_numbers = [s["scene_number"] for s in sarah_scenes]
        assert scene_numbers == expected_numbers
        
        print(f"✓ Multi-scene batch analysis successful: {len(data['breakdowns'])} breakdowns")
        return script_id
    
    def test_batch_analyze_empty_scenes_error(self):
        """Test that empty scenes list returns 400 error"""
        response = requests.post(
            f"{BASE_URL}/api/analyze/batch",
            json={
                "scenes": [],
                "character_name": "Sarah",
                "mode": "quick"
            },
            timeout=30
        )
        
        assert response.status_code == 400
        print("✓ Empty scenes list correctly rejected with 400")
    
    def test_batch_analyze_max_scenes_limit(self):
        """Test that more than 20 scenes returns 400 error"""
        # Create 21 fake scenes
        fake_scenes = [{"scene_number": i, "text": f"Scene {i} text", "heading": f"Scene {i}"} for i in range(21)]
        
        response = requests.post(
            f"{BASE_URL}/api/analyze/batch",
            json={
                "scenes": fake_scenes,
                "character_name": "Test",
                "mode": "quick"
            },
            timeout=30
        )
        
        assert response.status_code == 400
        assert "20" in response.json().get("detail", "")
        print("✓ More than 20 scenes correctly rejected with 400")


class TestGetScript:
    """Tests for GET /api/scripts/{script_id} endpoint"""
    
    def test_get_script_with_breakdowns(self):
        """Test retrieving a script with all its breakdowns"""
        # First create a script via batch analysis
        parse_response = requests.post(
            f"{BASE_URL}/api/parse-scenes",
            json={
                "text": SAMPLE_SCRIPT,
                "character_name": "Sarah"
            },
            timeout=60
        )
        parsed = parse_response.json()
        sarah_scenes = [s for s in parsed["scenes"] if s["has_character"]][:1]  # Just 1 scene
        
        batch_response = requests.post(
            f"{BASE_URL}/api/analyze/batch",
            json={
                "scenes": [{
                    "scene_number": s["scene_number"],
                    "text": s["text"],
                    "heading": s["heading"]
                } for s in sarah_scenes],
                "character_name": "Sarah",
                "mode": "quick"
            },
            timeout=120
        )
        
        assert batch_response.status_code == 200
        script_id = batch_response.json()["script_id"]
        
        # Now retrieve the script
        get_response = requests.get(
            f"{BASE_URL}/api/scripts/{script_id}",
            timeout=30
        )
        
        assert get_response.status_code == 200
        
        data = get_response.json()
        
        # Verify structure
        assert data["id"] == script_id
        assert "character_name" in data
        assert "mode" in data
        assert "scene_count" in data
        assert "breakdown_ids" in data
        assert "breakdowns" in data
        
        # Verify breakdowns are included
        assert len(data["breakdowns"]) == len(sarah_scenes)
        
        print(f"✓ Script {script_id} retrieved with {len(data['breakdowns'])} breakdowns")
    
    def test_get_script_not_found(self):
        """Test that non-existent script returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/scripts/nonexistent-script-id-12345",
            timeout=30
        )
        
        assert response.status_code == 404
        print("✓ Non-existent script correctly returns 404")


class TestRegressionExistingFlows:
    """Regression tests for existing Paste/Upload sides flows"""
    
    def test_analyze_text_quick_mode(self):
        """Test that existing text analysis still works (Quick mode)"""
        simple_sides = """JOHN
I didn't come here to argue.

SARAH
Then why did you come?

JOHN
You know why."""
        
        response = requests.post(
            f"{BASE_URL}/api/analyze/text",
            json={
                "text": simple_sides,
                "mode": "quick"
            },
            timeout=120
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "id" in data
        assert "scene_summary" in data
        assert "character_objective" in data
        assert "beats" in data
        assert "acting_takes" in data
        
        print(f"✓ Existing text analysis (Quick) still works, id: {data['id']}")
    
    def test_analyze_text_deep_mode(self):
        """Test that existing text analysis still works (Deep mode)"""
        simple_sides = """JOHN
I didn't come here to argue.

SARAH
Then why did you come?

JOHN
You know why."""
        
        response = requests.post(
            f"{BASE_URL}/api/analyze/text",
            json={
                "text": simple_sides,
                "mode": "deep"
            },
            timeout=180
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "id" in data
        assert "scene_summary" in data
        # Deep mode should have emotional_arc
        assert "emotional_arc" in data or data.get("mode") == "deep"
        
        print(f"✓ Existing text analysis (Deep) still works, id: {data['id']}")
    
    def test_get_breakdowns_list(self):
        """Test that breakdowns list endpoint still works"""
        response = requests.get(
            f"{BASE_URL}/api/breakdowns",
            timeout=30
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        print(f"✓ Breakdowns list endpoint works, {len(data)} breakdowns found")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
