"""
Test suite for Actor's Companion pipeline debug and analysis features.
Tests the new _debug tracking, fallback responses, and stage-by-stage pipeline testing.
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestDebugPipeline:
    """Tests for /api/debug/pipeline endpoint - independent stage testing"""
    
    def test_debug_pipeline_returns_all_stages(self):
        """GET /api/debug/pipeline should return all_ok:true with all stages"""
        response = requests.get(f"{BASE_URL}/api/debug/pipeline", timeout=60)
        assert response.status_code == 200
        
        data = response.json()
        assert "all_ok" in data
        assert "stages" in data
        
        # Verify all expected stages are present
        expected_stages = ["llm_key", "gpt_call", "mongodb", "image_processing", "heic_support", "pdf_support"]
        for stage in expected_stages:
            assert stage in data["stages"], f"Missing stage: {stage}"
            assert "ok" in data["stages"][stage], f"Stage {stage} missing 'ok' field"
    
    def test_debug_pipeline_all_stages_pass(self):
        """All pipeline stages should pass (ok: true)"""
        response = requests.get(f"{BASE_URL}/api/debug/pipeline", timeout=60)
        assert response.status_code == 200
        
        data = response.json()
        assert data["all_ok"] == True, f"Pipeline not all_ok: {data}"
        
        for stage_name, stage_data in data["stages"].items():
            assert stage_data.get("ok") == True, f"Stage {stage_name} failed: {stage_data}"


class TestAnalyzeText:
    """Tests for /api/analyze/text endpoint with _debug tracking"""
    
    def test_analyze_text_success_with_debug(self):
        """POST /api/analyze/text should return 200 with _debug.stages and _debug.fallback=false"""
        payload = {
            "text": "JOHN\nI didn't come here to argue.\n\nSARAH\nThen why did you come?\n\nJOHN\nBecause I need you to hear this."
        }
        response = requests.post(f"{BASE_URL}/api/analyze/text", json=payload, timeout=120)
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify _debug object exists
        assert "_debug" in data, "Response missing _debug object"
        debug = data["_debug"]
        
        # Verify fallback is false for successful analysis
        assert debug.get("fallback") == False, f"Expected fallback=false, got {debug.get('fallback')}"
        
        # Verify stages array exists
        assert "stages" in debug, "Missing stages in _debug"
        stages = debug["stages"]
        assert len(stages) > 0, "Stages array is empty"
    
    def test_analyze_text_stages_include_required(self):
        """_debug.stages should include input_received, gpt_analysis, db_save all with ok:true"""
        payload = {
            "text": "JOHN\nI didn't come here to argue.\n\nSARAH\nThen why did you come?"
        }
        response = requests.post(f"{BASE_URL}/api/analyze/text", json=payload, timeout=120)
        assert response.status_code == 200
        
        data = response.json()
        stages = data.get("_debug", {}).get("stages", [])
        
        # Convert to dict for easier lookup
        stage_dict = {s["stage"]: s for s in stages}
        
        # Verify required stages
        required_stages = ["input_received", "gpt_analysis", "db_save"]
        for stage_name in required_stages:
            assert stage_name in stage_dict, f"Missing stage: {stage_name}"
            assert stage_dict[stage_name].get("ok") == True, f"Stage {stage_name} not ok"
    
    def test_analyze_text_empty_returns_400(self):
        """POST /api/analyze/text with empty text should return 400"""
        payload = {"text": ""}
        response = requests.post(f"{BASE_URL}/api/analyze/text", json=payload, timeout=30)
        assert response.status_code == 400
        assert "detail" in response.json()
    
    def test_analyze_text_too_short_returns_400(self):
        """POST /api/analyze/text with text < 10 chars should return 400"""
        payload = {"text": "Hi"}
        response = requests.post(f"{BASE_URL}/api/analyze/text", json=payload, timeout=30)
        assert response.status_code == 400


class TestAnalyzeImage:
    """Tests for /api/analyze/image endpoint with _debug tracking"""
    
    def test_analyze_image_jpeg_success(self):
        """POST /api/analyze/image with JPEG should return 200 with proper stages"""
        with open("/tmp/test_sides.jpg", "rb") as f:
            files = {"file": ("test_sides.jpg", f, "image/jpeg")}
            response = requests.post(f"{BASE_URL}/api/analyze/image", files=files, timeout=120)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify _debug
        assert "_debug" in data
        debug = data["_debug"]
        assert debug.get("fallback") == False
        
        # Verify stages
        stages = debug.get("stages", [])
        stage_names = [s["stage"] for s in stages]
        
        # JPEG should have these stages
        assert "file_received" in stage_names
        assert "type_detection" in stage_names
        assert "image_convert" in stage_names
        assert "gpt_vision" in stage_names
        assert "db_save" in stage_names
    
    def test_analyze_image_pdf_success(self):
        """POST /api/analyze/image with PDF should return 200 with proper stages"""
        with open("/tmp/test_sides.pdf", "rb") as f:
            files = {"file": ("test_sides.pdf", f, "application/pdf")}
            response = requests.post(f"{BASE_URL}/api/analyze/image", files=files, timeout=120)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify _debug
        assert "_debug" in data
        debug = data["_debug"]
        assert debug.get("fallback") == False
        
        # Verify stages
        stages = debug.get("stages", [])
        stage_names = [s["stage"] for s in stages]
        
        # PDF should have these stages
        assert "file_received" in stage_names
        assert "type_detection" in stage_names
        assert "pdf_extract" in stage_names
        assert "gpt_analysis" in stage_names
        assert "db_save" in stage_names
    
    def test_analyze_image_octet_stream_ios_edge_case(self):
        """POST /api/analyze/image with application/octet-stream (iOS edge case) should detect as image"""
        with open("/tmp/test_sides.jpg", "rb") as f:
            files = {"file": ("photo.jpg", f, "application/octet-stream")}
            response = requests.post(f"{BASE_URL}/api/analyze/image", files=files, timeout=120)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should succeed, not fallback
        debug = data.get("_debug", {})
        assert debug.get("fallback") == False, f"iOS octet-stream should succeed, got fallback: {debug}"
        
        # Verify type was detected as image
        stages = debug.get("stages", [])
        type_stage = next((s for s in stages if s["stage"] == "type_detection"), None)
        assert type_stage is not None
        assert type_stage.get("detected") == "image"
    
    def test_analyze_image_empty_file_returns_400(self):
        """POST /api/analyze/image with empty file should return 400"""
        # Create empty file
        with open("/tmp/empty_test.jpg", "wb") as f:
            pass
        
        with open("/tmp/empty_test.jpg", "rb") as f:
            files = {"file": ("empty.jpg", f, "image/jpeg")}
            response = requests.post(f"{BASE_URL}/api/analyze/image", files=files, timeout=30)
        
        assert response.status_code == 400
        assert "empty" in response.json().get("detail", "").lower()
    
    def test_analyze_image_unsupported_file_returns_fallback(self):
        """POST /api/analyze/image with unsupported file should return fallback response"""
        # Create a text file
        with open("/tmp/test_unsupported.txt", "w") as f:
            f.write("This is not an image")
        
        with open("/tmp/test_unsupported.txt", "rb") as f:
            files = {"file": ("test.txt", f, "text/plain")}
            response = requests.post(f"{BASE_URL}/api/analyze/image", files=files, timeout=30)
        
        # Should return 200 with fallback, not 400/500
        assert response.status_code == 200
        data = response.json()
        
        debug = data.get("_debug", {})
        assert debug.get("fallback") == True, "Unsupported file should trigger fallback"
        assert "reason" in debug


class TestBreakdowns:
    """Tests for /api/breakdowns endpoints"""
    
    def test_list_breakdowns(self):
        """GET /api/breakdowns should return list of breakdowns"""
        response = requests.get(f"{BASE_URL}/api/breakdowns", timeout=30)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        if len(data) > 0:
            # Verify breakdown structure
            breakdown = data[0]
            assert "id" in breakdown
            assert "character_name" in breakdown or "scene_summary" in breakdown


class TestRegenerateTakes:
    """Tests for /api/regenerate-takes endpoint (regression check)"""
    
    def test_regenerate_takes_success(self):
        """POST /api/regenerate-takes/{id} should still work"""
        # First get a breakdown ID
        list_response = requests.get(f"{BASE_URL}/api/breakdowns", timeout=30)
        assert list_response.status_code == 200
        
        breakdowns = list_response.json()
        if len(breakdowns) == 0:
            pytest.skip("No breakdowns available for regenerate test")
        
        breakdown_id = breakdowns[0]["id"]
        
        # Test regenerate
        response = requests.post(f"{BASE_URL}/api/regenerate-takes/{breakdown_id}", timeout=120)
        assert response.status_code == 200
        
        data = response.json()
        assert "acting_takes" in data
        takes = data["acting_takes"]
        assert "grounded" in takes
        assert "bold" in takes
        assert "wildcard" in takes
    
    def test_regenerate_takes_not_found(self):
        """POST /api/regenerate-takes with invalid ID should return 404"""
        response = requests.post(f"{BASE_URL}/api/regenerate-takes/invalid-id-12345", timeout=30)
        assert response.status_code == 404
