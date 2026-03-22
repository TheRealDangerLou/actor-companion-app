"""
Test suite for cost optimization features:
- Caching layer (compute_cache_key, get_cached_breakdown, store_cached_breakdown)
- /api/debug/pipeline endpoint (no GPT calls, shows cache stats)
- /api/check-cache and /api/check-cache/batch endpoints
- /api/analyze/text and /api/analyze/scene cache behavior
- Scene text hard cap (8000 chars)
"""
import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestDebugPipeline:
    """Test /api/debug/pipeline endpoint - should NOT make GPT calls"""
    
    def test_debug_pipeline_has_gpt_ready_not_gpt_call(self):
        """Verify debug/pipeline has 'gpt_ready' field with no actual GPT test call"""
        response = requests.get(f"{BASE_URL}/api/debug/pipeline", timeout=30)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "stages" in data, "Response should have 'stages' field"
        
        # Should have gpt_ready, NOT gpt_call
        assert "gpt_ready" in data["stages"], "Should have 'gpt_ready' field"
        assert "gpt_call" not in data["stages"], "Should NOT have 'gpt_call' field (no GPT test call)"
        
        # Verify gpt_ready structure
        gpt_ready = data["stages"]["gpt_ready"]
        assert "ok" in gpt_ready, "gpt_ready should have 'ok' field"
        assert "note" in gpt_ready, "gpt_ready should have 'note' field"
        assert "cost savings" in gpt_ready["note"].lower(), "Note should mention cost savings"
        print(f"PASS: debug/pipeline has gpt_ready (no GPT call): {gpt_ready}")
    
    def test_debug_pipeline_has_cache_stats(self):
        """Verify debug/pipeline shows cache statistics"""
        response = requests.get(f"{BASE_URL}/api/debug/pipeline", timeout=30)
        assert response.status_code == 200
        
        data = response.json()
        assert "cache" in data["stages"], "Should have 'cache' field in stages"
        
        cache_info = data["stages"]["cache"]
        assert "ok" in cache_info, "cache should have 'ok' field"
        assert "cached_breakdowns" in cache_info, "cache should have 'cached_breakdowns' count"
        assert "version" in cache_info, "cache should have 'version' field"
        assert "ttl_hours" in cache_info, "cache should have 'ttl_hours' field"
        
        print(f"PASS: debug/pipeline shows cache stats: {cache_info}")


class TestCheckCacheEndpoint:
    """Test /api/check-cache endpoint for cost estimation"""
    
    def test_check_cache_new_text_quick_mode(self):
        """New text with quick mode should return cached=false, estimated_cost=0.03"""
        unique_text = f"UNIQUE_TEST_{uuid.uuid4()}\nJOHN\nI didn't come here to argue.\n\nSARAH\nThen why did you come?"
        
        response = requests.post(
            f"{BASE_URL}/api/check-cache",
            json={"text": unique_text, "mode": "quick"},
            timeout=30
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "cached" in data, "Response should have 'cached' field"
        assert "estimated_cost" in data, "Response should have 'estimated_cost' field"
        
        assert data["cached"] == False, "New text should not be cached"
        assert data["estimated_cost"] == 0.03, f"Quick mode cost should be 0.03, got {data['estimated_cost']}"
        
        print(f"PASS: check-cache new text quick mode: cached={data['cached']}, cost={data['estimated_cost']}")
    
    def test_check_cache_new_text_deep_mode(self):
        """New text with deep mode should return cached=false, estimated_cost=0.08"""
        unique_text = f"UNIQUE_TEST_DEEP_{uuid.uuid4()}\nJOHN\nI didn't come here to argue.\n\nSARAH\nThen why did you come?"
        
        response = requests.post(
            f"{BASE_URL}/api/check-cache",
            json={"text": unique_text, "mode": "deep"},
            timeout=30
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["cached"] == False, "New text should not be cached"
        assert data["estimated_cost"] == 0.08, f"Deep mode cost should be 0.08, got {data['estimated_cost']}"
        
        print(f"PASS: check-cache new text deep mode: cached={data['cached']}, cost={data['estimated_cost']}")


class TestCheckCacheBatchEndpoint:
    """Test /api/check-cache/batch endpoint for batch cost estimation"""
    
    def test_check_cache_batch_multiple_scenes(self):
        """Batch check should return correct cached/uncached counts and estimated cost"""
        scenes = [
            {"text": f"SCENE_BATCH_1_{uuid.uuid4()}\nJOHN\nLine one.", "scene_number": 1},
            {"text": f"SCENE_BATCH_2_{uuid.uuid4()}\nSARAH\nLine two.", "scene_number": 2},
            {"text": f"SCENE_BATCH_3_{uuid.uuid4()}\nJOHN\nLine three.", "scene_number": 3},
        ]
        
        response = requests.post(
            f"{BASE_URL}/api/check-cache/batch",
            json={"scenes": scenes, "mode": "quick", "character_name": "JOHN"},
            timeout=30
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "total" in data, "Response should have 'total' field"
        assert "cached" in data, "Response should have 'cached' field"
        assert "uncached" in data, "Response should have 'uncached' field"
        assert "estimated_cost" in data, "Response should have 'estimated_cost' field"
        assert "scenes" in data, "Response should have 'scenes' field"
        
        assert data["total"] == 3, f"Total should be 3, got {data['total']}"
        # All new scenes should be uncached
        assert data["uncached"] == 3, f"Uncached should be 3, got {data['uncached']}"
        # Cost = 3 scenes * 0.03 (quick mode) = 0.09
        assert data["estimated_cost"] == 0.09, f"Estimated cost should be 0.09, got {data['estimated_cost']}"
        
        print(f"PASS: check-cache/batch: total={data['total']}, cached={data['cached']}, uncached={data['uncached']}, cost={data['estimated_cost']}")
    
    def test_check_cache_batch_deep_mode(self):
        """Batch check with deep mode should have higher cost estimate"""
        scenes = [
            {"text": f"SCENE_DEEP_1_{uuid.uuid4()}\nJOHN\nLine one.", "scene_number": 1},
            {"text": f"SCENE_DEEP_2_{uuid.uuid4()}\nSARAH\nLine two.", "scene_number": 2},
        ]
        
        response = requests.post(
            f"{BASE_URL}/api/check-cache/batch",
            json={"scenes": scenes, "mode": "deep", "character_name": "JOHN"},
            timeout=30
        )
        assert response.status_code == 200
        
        data = response.json()
        # Cost = 2 scenes * 0.08 (deep mode) = 0.16
        assert data["estimated_cost"] == 0.16, f"Deep mode cost should be 0.16, got {data['estimated_cost']}"
        
        print(f"PASS: check-cache/batch deep mode: cost={data['estimated_cost']}")


class TestAnalyzeTextCaching:
    """Test /api/analyze/text endpoint caching behavior"""
    
    def test_analyze_text_caches_and_returns_from_cache(self):
        """First call should cache, second identical call should return from_cache=true"""
        # Use a unique but consistent text for this test
        test_text = f"CACHE_TEST_{int(time.time())}\nJOHN\nI didn't come here to argue.\n\nSARAH\nThen why did you come?"
        
        # First call - should make GPT call and cache
        print("Making first analyze/text call (should cache)...")
        response1 = requests.post(
            f"{BASE_URL}/api/analyze/text",
            json={"text": test_text, "mode": "quick"},
            timeout=120
        )
        assert response1.status_code == 200, f"First call failed: {response1.status_code} - {response1.text[:200]}"
        
        data1 = response1.json()
        assert "id" in data1, "Response should have 'id' field"
        assert "scene_summary" in data1, "Response should have 'scene_summary' field"
        
        # Check if first call was from cache (it shouldn't be for new text)
        from_cache_1 = data1.get("from_cache", False)
        print(f"First call: from_cache={from_cache_1}")
        
        # Second call with EXACT same text - should return from cache
        print("Making second analyze/text call (should be from cache)...")
        response2 = requests.post(
            f"{BASE_URL}/api/analyze/text",
            json={"text": test_text, "mode": "quick"},
            timeout=120
        )
        assert response2.status_code == 200, f"Second call failed: {response2.status_code}"
        
        data2 = response2.json()
        from_cache_2 = data2.get("from_cache", False)
        
        assert from_cache_2 == True, f"Second call should have from_cache=true, got {from_cache_2}"
        print(f"PASS: Second call returned from_cache={from_cache_2}")


class TestAnalyzeSceneCaching:
    """Test /api/analyze/scene endpoint caching behavior"""
    
    def test_analyze_scene_caches_and_returns_from_cache(self):
        """First call should cache, second identical call should return from_cache=true"""
        # Create a script first
        script_response = requests.post(
            f"{BASE_URL}/api/scripts/create",
            json={"character_name": "JOHN", "mode": "quick", "scene_count": 1},
            timeout=30
        )
        assert script_response.status_code == 200
        script_id = script_response.json()["script_id"]
        
        # Unique scene text
        scene_text = f"SCENE_CACHE_TEST_{int(time.time())}\nJOHN\nI didn't come here to argue.\n\nSARAH\nThen why did you come?"
        
        # First call
        print("Making first analyze/scene call (should cache)...")
        response1 = requests.post(
            f"{BASE_URL}/api/analyze/scene",
            json={
                "script_id": script_id,
                "scene_number": 1,
                "scene_heading": "INT. KITCHEN - DAY",
                "text": scene_text,
                "character_name": "JOHN",
                "mode": "quick"
            },
            timeout=120
        )
        assert response1.status_code == 200, f"First call failed: {response1.status_code}"
        
        data1 = response1.json()
        from_cache_1 = data1.get("from_cache", False)
        print(f"First call: from_cache={from_cache_1}")
        
        # Create another script for second call
        script_response2 = requests.post(
            f"{BASE_URL}/api/scripts/create",
            json={"character_name": "JOHN", "mode": "quick", "scene_count": 1},
            timeout=30
        )
        script_id2 = script_response2.json()["script_id"]
        
        # Second call with same text
        print("Making second analyze/scene call (should be from cache)...")
        response2 = requests.post(
            f"{BASE_URL}/api/analyze/scene",
            json={
                "script_id": script_id2,
                "scene_number": 1,
                "scene_heading": "INT. KITCHEN - DAY",
                "text": scene_text,
                "character_name": "JOHN",
                "mode": "quick"
            },
            timeout=120
        )
        assert response2.status_code == 200
        
        data2 = response2.json()
        from_cache_2 = data2.get("from_cache", False)
        
        assert from_cache_2 == True, f"Second call should have from_cache=true, got {from_cache_2}"
        print(f"PASS: Second analyze/scene call returned from_cache={from_cache_2}")


class TestSceneTextHardCap:
    """Test that scene text exceeding 8000 chars is hard-capped"""
    
    def test_analyze_text_hard_cap(self):
        """Text exceeding 8000 chars should be truncated"""
        # Create text longer than 8000 chars
        long_text = "JOHN\n" + ("This is a very long line of dialogue that goes on and on. " * 200)
        assert len(long_text) > 8000, f"Test text should be >8000 chars, got {len(long_text)}"
        
        response = requests.post(
            f"{BASE_URL}/api/analyze/text",
            json={"text": long_text, "mode": "quick"},
            timeout=120
        )
        assert response.status_code == 200, f"Request failed: {response.status_code}"
        
        data = response.json()
        # The original_text in response should be capped at 8000
        original_text = data.get("original_text", "")
        assert len(original_text) <= 8000, f"original_text should be <=8000 chars, got {len(original_text)}"
        
        print(f"PASS: Long text was hard-capped. Input: {len(long_text)} chars, Output: {len(original_text)} chars")
    
    def test_analyze_scene_hard_cap(self):
        """Scene text exceeding 8000 chars should be truncated"""
        # Create script
        script_response = requests.post(
            f"{BASE_URL}/api/scripts/create",
            json={"character_name": "JOHN", "mode": "quick", "scene_count": 1},
            timeout=30
        )
        script_id = script_response.json()["script_id"]
        
        # Create text longer than 8000 chars
        long_text = "JOHN\n" + ("This is a very long scene text that exceeds the limit. " * 200)
        assert len(long_text) > 8000
        
        response = requests.post(
            f"{BASE_URL}/api/analyze/scene",
            json={
                "script_id": script_id,
                "scene_number": 1,
                "scene_heading": "INT. LONG SCENE - DAY",
                "text": long_text,
                "character_name": "JOHN",
                "mode": "quick"
            },
            timeout=120
        )
        assert response.status_code == 200
        
        data = response.json()
        original_text = data.get("original_text", "")
        assert len(original_text) <= 8000, f"original_text should be <=8000 chars, got {len(original_text)}"
        
        print(f"PASS: Scene text was hard-capped. Input: {len(long_text)} chars, Output: {len(original_text)} chars")


@pytest.fixture(scope="session", autouse=True)
def check_base_url():
    """Ensure BASE_URL is set"""
    if not BASE_URL:
        pytest.skip("REACT_APP_BACKEND_URL not set")
    print(f"Testing against: {BASE_URL}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
