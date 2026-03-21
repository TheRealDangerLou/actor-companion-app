"""
Test suite for My Lines tab and Memorization Mode features
Tests the new 'My Lines' speed drill tab and regression tests for existing memorization tabs
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
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"SUCCESS: API root returns: {data}")

class TestBreakdownsAPI:
    """Test breakdowns list and retrieval"""
    
    def test_get_breakdowns_list(self):
        """Test GET /api/breakdowns returns list"""
        response = requests.get(f"{BASE_URL}/api/breakdowns")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"SUCCESS: GET /api/breakdowns returns {len(data)} breakdowns")
        return data
    
    def test_breakdown_has_memorization_data(self):
        """Test that breakdowns have memorization data structure"""
        response = requests.get(f"{BASE_URL}/api/breakdowns")
        assert response.status_code == 200
        breakdowns = response.json()
        
        if len(breakdowns) == 0:
            pytest.skip("No breakdowns available to test")
        
        # Get the first breakdown with memorization data
        breakdown_id = breakdowns[0].get('id')
        detail_response = requests.get(f"{BASE_URL}/api/breakdowns/{breakdown_id}")
        assert detail_response.status_code == 200
        
        breakdown = detail_response.json()
        assert 'memorization' in breakdown, "Breakdown should have memorization field"
        
        memorization = breakdown['memorization']
        if memorization:
            # Check for cue_recall array (used by My Lines and Line Run tabs)
            assert 'cue_recall' in memorization, "Memorization should have cue_recall"
            assert isinstance(memorization['cue_recall'], list)
            
            # Check for chunked_lines array (used by Reader tab)
            assert 'chunked_lines' in memorization, "Memorization should have chunked_lines"
            assert isinstance(memorization['chunked_lines'], list)
            
            print(f"SUCCESS: Breakdown {breakdown_id} has memorization with {len(memorization['cue_recall'])} cue_recall items and {len(memorization['chunked_lines'])} chunks")
        else:
            print(f"INFO: Breakdown {breakdown_id} has null memorization (may be expected for some content)")

class TestAnalyzeTextAPI:
    """Test text analysis endpoint with memorization data"""
    
    def test_analyze_text_quick_mode(self):
        """Test POST /api/analyze/text with mode=quick returns valid breakdown with memorization"""
        test_script = """JOHN
I didn't come here to argue.

SARAH
Then why did you come?

JOHN
Because I need you to hear this. Before it's too late."""
        
        response = requests.post(
            f"{BASE_URL}/api/analyze/text",
            json={"text": test_script, "mode": "quick"},
            timeout=120
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check basic breakdown structure
        assert 'id' in data, "Response should have id"
        assert 'character_name' in data, "Response should have character_name"
        assert 'memorization' in data, "Response should have memorization"
        
        # Check memorization structure for My Lines tab
        memorization = data.get('memorization', {})
        if memorization:
            cue_recall = memorization.get('cue_recall', [])
            chunked_lines = memorization.get('chunked_lines', [])
            
            print(f"SUCCESS: Quick mode analysis returned breakdown with:")
            print(f"  - Character: {data.get('character_name')}")
            print(f"  - {len(cue_recall)} cue_recall items (for My Lines/Line Run)")
            print(f"  - {len(chunked_lines)} chunked_lines (for Reader)")
            
            # Verify cue_recall structure (needed for My Lines tab)
            if len(cue_recall) > 0:
                first_cue = cue_recall[0]
                assert 'cue' in first_cue, "cue_recall item should have 'cue' field"
                assert 'your_line' in first_cue, "cue_recall item should have 'your_line' field"
                print(f"  - First cue: '{first_cue.get('cue', '')[:50]}...'")
                print(f"  - First your_line: '{first_cue.get('your_line', '')[:50]}...'")
        
        return data

class TestMemorizationDataStructure:
    """Test memorization data structure for all tabs"""
    
    def test_cue_recall_format(self):
        """Test cue_recall has correct format for My Lines and Line Run tabs"""
        response = requests.get(f"{BASE_URL}/api/breakdowns")
        breakdowns = response.json()
        
        if len(breakdowns) == 0:
            pytest.skip("No breakdowns available")
        
        # Find a breakdown with cue_recall data
        for b in breakdowns:
            detail = requests.get(f"{BASE_URL}/api/breakdowns/{b['id']}").json()
            memorization = detail.get('memorization', {})
            cue_recall = memorization.get('cue_recall', []) if memorization else []
            
            if len(cue_recall) > 0:
                for i, item in enumerate(cue_recall):
                    assert 'cue' in item, f"cue_recall[{i}] missing 'cue' field"
                    assert 'your_line' in item, f"cue_recall[{i}] missing 'your_line' field"
                
                print(f"SUCCESS: cue_recall format verified with {len(cue_recall)} items")
                return
        
        print("INFO: No breakdowns with cue_recall data found")
    
    def test_chunked_lines_format(self):
        """Test chunked_lines has correct format for Reader tab"""
        response = requests.get(f"{BASE_URL}/api/breakdowns")
        breakdowns = response.json()
        
        if len(breakdowns) == 0:
            pytest.skip("No breakdowns available")
        
        # Find a breakdown with chunked_lines data
        for b in breakdowns:
            detail = requests.get(f"{BASE_URL}/api/breakdowns/{b['id']}").json()
            memorization = detail.get('memorization', {})
            chunked_lines = memorization.get('chunked_lines', []) if memorization else []
            
            if len(chunked_lines) > 0:
                for i, chunk in enumerate(chunked_lines):
                    assert 'chunk_label' in chunk, f"chunked_lines[{i}] missing 'chunk_label'"
                    assert 'lines' in chunk, f"chunked_lines[{i}] missing 'lines'"
                
                print(f"SUCCESS: chunked_lines format verified with {len(chunked_lines)} chunks")
                return
        
        print("INFO: No breakdowns with chunked_lines data found")

class TestTTSStatus:
    """Test TTS status endpoint"""
    
    def test_tts_status(self):
        """Test GET /api/tts/status returns availability"""
        response = requests.get(f"{BASE_URL}/api/tts/status")
        assert response.status_code == 200
        data = response.json()
        assert 'available' in data
        print(f"SUCCESS: TTS status: available={data.get('available')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
