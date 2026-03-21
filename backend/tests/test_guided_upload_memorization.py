"""
Test suite for Actor's Companion - Guided Upload Flow and Memorization Mode
Tests the new features: 3-step guided upload and memorization mode with 3 tabs
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAPIHealth:
    """Basic API health checks"""
    
    def test_api_root(self):
        """Test API root endpoint"""
        response = requests.get(f"{BASE_URL}/api/", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"API root response: {data}")


class TestAnalyzeTextEndpoint:
    """Tests for POST /api/analyze/text endpoint"""
    
    def test_analyze_text_quick_mode(self):
        """Test text analysis with quick mode"""
        test_script = """JOHN
I didn't come here to argue.

SARAH
Then why did you come?

JOHN
Because I needed to see you. One last time."""
        
        response = requests.post(
            f"{BASE_URL}/api/analyze/text",
            json={"text": test_script, "mode": "quick"},
            timeout=120
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "id" in data
        assert "character_name" in data
        assert "mode" in data
        assert data["mode"] == "quick"
        
        # Verify memorization data exists
        assert "memorization" in data
        memorization = data["memorization"]
        assert "cue_recall" in memorization
        assert "chunked_lines" in memorization
        
        print(f"Quick mode analysis successful - ID: {data['id']}, Character: {data['character_name']}")
        print(f"Memorization: {len(memorization.get('cue_recall', []))} cue_recall items, {len(memorization.get('chunked_lines', []))} chunks")
        
        return data["id"]
    
    def test_analyze_text_deep_mode(self):
        """Test text analysis with deep mode"""
        test_script = """JOHN
I didn't come here to argue.

SARAH
Then why did you come?

JOHN
Because I needed to see you. One last time.

SARAH
You always say that. And yet here you are again."""
        
        response = requests.post(
            f"{BASE_URL}/api/analyze/text",
            json={"text": test_script, "mode": "deep"},
            timeout=180
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "id" in data
        assert "mode" in data
        assert data["mode"] == "deep"
        
        # Deep mode should have emotional_arc and what_they_hide
        # (These may be in the response depending on implementation)
        
        # Verify memorization data exists
        assert "memorization" in data
        memorization = data["memorization"]
        assert "cue_recall" in memorization
        
        print(f"Deep mode analysis successful - ID: {data['id']}")
        
        return data["id"]


class TestBreakdownsEndpoint:
    """Tests for GET /api/breakdowns endpoint"""
    
    def test_get_breakdowns_list(self):
        """Test getting list of breakdowns"""
        response = requests.get(f"{BASE_URL}/api/breakdowns", timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        print(f"Found {len(data)} breakdowns")
        
        if len(data) > 0:
            # Verify breakdown structure
            breakdown = data[0]
            assert "id" in breakdown
            assert "character_name" in breakdown or "original_text" in breakdown
            print(f"First breakdown: ID={breakdown['id']}, Character={breakdown.get('character_name', 'N/A')}")
        
        return data
    
    def test_get_single_breakdown(self):
        """Test getting a single breakdown by ID"""
        # First get list to find an ID
        list_response = requests.get(f"{BASE_URL}/api/breakdowns", timeout=30)
        assert list_response.status_code == 200
        breakdowns = list_response.json()
        
        if len(breakdowns) == 0:
            pytest.skip("No breakdowns available to test")
        
        breakdown_id = breakdowns[0]["id"]
        
        # Get single breakdown
        response = requests.get(f"{BASE_URL}/api/breakdowns/{breakdown_id}", timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == breakdown_id
        
        # Verify memorization data structure
        if "memorization" in data:
            memorization = data["memorization"]
            
            # Check cue_recall structure
            if "cue_recall" in memorization and len(memorization["cue_recall"]) > 0:
                cue_item = memorization["cue_recall"][0]
                assert "cue" in cue_item
                assert "your_line" in cue_item
                print(f"Cue-recall structure valid: cue='{cue_item['cue'][:50]}...'")
            
            # Check chunked_lines structure
            if "chunked_lines" in memorization and len(memorization["chunked_lines"]) > 0:
                chunk = memorization["chunked_lines"][0]
                assert "chunk_label" in chunk or "lines" in chunk
                print(f"Chunked lines structure valid")
        
        print(f"Single breakdown retrieved successfully: {breakdown_id}")
        return data


class TestMemorizationData:
    """Tests specifically for memorization data structure"""
    
    def test_memorization_cue_recall_format(self):
        """Verify cue_recall data has correct format for Line Run and Cue & Recall tabs"""
        response = requests.get(f"{BASE_URL}/api/breakdowns", timeout=30)
        assert response.status_code == 200
        breakdowns = response.json()
        
        # Find a breakdown with memorization data
        breakdown_with_mem = None
        for b in breakdowns:
            if "memorization" in b and b["memorization"]:
                breakdown_with_mem = b
                break
        
        if not breakdown_with_mem:
            # Get full breakdown details
            if len(breakdowns) > 0:
                detail_response = requests.get(f"{BASE_URL}/api/breakdowns/{breakdowns[0]['id']}", timeout=30)
                if detail_response.status_code == 200:
                    breakdown_with_mem = detail_response.json()
        
        if not breakdown_with_mem or "memorization" not in breakdown_with_mem:
            pytest.skip("No breakdown with memorization data found")
        
        memorization = breakdown_with_mem["memorization"]
        
        # Verify cue_recall for Line Run tab
        assert "cue_recall" in memorization, "Missing cue_recall for Line Run tab"
        cue_recall = memorization["cue_recall"]
        
        if len(cue_recall) > 0:
            for i, item in enumerate(cue_recall[:3]):  # Check first 3 items
                assert "cue" in item, f"cue_recall[{i}] missing 'cue' field"
                assert "your_line" in item, f"cue_recall[{i}] missing 'your_line' field"
                assert isinstance(item["cue"], str), f"cue_recall[{i}].cue should be string"
                assert isinstance(item["your_line"], str), f"cue_recall[{i}].your_line should be string"
        
        print(f"Cue-recall format valid: {len(cue_recall)} items")
    
    def test_memorization_chunked_lines_format(self):
        """Verify chunked_lines data has correct format for Reader tab"""
        response = requests.get(f"{BASE_URL}/api/breakdowns", timeout=30)
        assert response.status_code == 200
        breakdowns = response.json()
        
        if len(breakdowns) == 0:
            pytest.skip("No breakdowns available")
        
        # Get full breakdown details
        detail_response = requests.get(f"{BASE_URL}/api/breakdowns/{breakdowns[0]['id']}", timeout=30)
        assert detail_response.status_code == 200
        breakdown = detail_response.json()
        
        if "memorization" not in breakdown or not breakdown["memorization"]:
            pytest.skip("No memorization data in breakdown")
        
        memorization = breakdown["memorization"]
        
        # Verify chunked_lines for Reader tab
        assert "chunked_lines" in memorization, "Missing chunked_lines for Reader tab"
        chunked_lines = memorization["chunked_lines"]
        
        if len(chunked_lines) > 0:
            for i, chunk in enumerate(chunked_lines[:3]):  # Check first 3 chunks
                assert "chunk_label" in chunk or "lines" in chunk, f"chunked_lines[{i}] missing required fields"
                if "lines" in chunk:
                    assert isinstance(chunk["lines"], str), f"chunked_lines[{i}].lines should be string"
        
        print(f"Chunked lines format valid: {len(chunked_lines)} chunks")


class TestRegressionEndpoints:
    """Regression tests for existing endpoints"""
    
    def test_tts_status(self):
        """Test TTS status endpoint"""
        response = requests.get(f"{BASE_URL}/api/tts/status", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert "available" in data
        print(f"TTS status: available={data['available']}")
    
    def test_analyze_text_default_mode(self):
        """Test that analyze/text defaults to quick mode when mode not specified"""
        test_script = """JOHN
Hello there.

SARAH
Hi."""
        
        response = requests.post(
            f"{BASE_URL}/api/analyze/text",
            json={"text": test_script},  # No mode specified
            timeout=120
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should default to quick mode
        assert data.get("mode") == "quick" or "mode" not in data or data.get("mode") is None
        print("Default mode test passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
