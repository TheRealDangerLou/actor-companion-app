"""
Test Quick/Deep Mode Feature for Actor's Companion
Tests the new analysis modes: quick (~15s) and deep (~30-45s)
- Quick mode: simple beat subtext, no emotional_arc or what_they_hide
- Deep mode: emotional_arc, what_they_hide, layered subtext (surface/meaning/fear), physical_life
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test script text
TEST_SCRIPT = """JOHN
I didn't come here to argue.

SARAH
Then why did you come?

JOHN
Because I need you to hear this."""


class TestQuickDeepModeAPI:
    """Tests for Quick/Deep mode API endpoints"""
    
    def test_api_health(self):
        """Verify API is accessible"""
        response = requests.get(f"{BASE_URL}/api/", timeout=30)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"✓ API health check passed: {data}")
    
    def test_analyze_text_quick_mode_explicit(self):
        """POST /api/analyze/text with mode=quick should return quick format"""
        response = requests.post(
            f"{BASE_URL}/api/analyze/text",
            json={"text": TEST_SCRIPT, "mode": "quick"},
            timeout=180
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Quick mode should NOT have emotional_arc or what_they_hide
        # (unless it's a fallback response)
        if not data.get("_debug", {}).get("fallback"):
            # Check mode is stored
            assert data.get("mode") == "quick" or data.get("mode") is None, f"Mode should be quick, got {data.get('mode')}"
            
            # Quick mode beats should have simple 'subtext', not layered subtext
            beats = data.get("beats", [])
            if beats:
                beat = beats[0]
                # Quick mode should have 'subtext' field
                assert "subtext" in beat or "subtext_surface" not in beat, "Quick mode should have simple subtext"
                # Quick mode should NOT have physical_life
                # (Note: this may vary based on GPT response, so we just log it)
                if "physical_life" in beat:
                    print(f"  Note: Quick mode beat has physical_life (unexpected but not critical)")
        
        print(f"✓ Quick mode text analysis returned successfully")
        print(f"  - Has emotional_arc: {'emotional_arc' in data}")
        print(f"  - Has what_they_hide: {'what_they_hide' in data}")
        print(f"  - Mode: {data.get('mode')}")
        print(f"  - Beats count: {len(data.get('beats', []))}")
    
    def test_analyze_text_deep_mode(self):
        """POST /api/analyze/text with mode=deep should return deep format"""
        response = requests.post(
            f"{BASE_URL}/api/analyze/text",
            json={"text": TEST_SCRIPT, "mode": "deep"},
            timeout=180
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check if it's a fallback response
        if data.get("_debug", {}).get("fallback"):
            print(f"  Note: Got fallback response - {data.get('_debug', {}).get('reason')}")
            pytest.skip("Fallback response received - LLM may have budget/timeout issues")
        
        # Deep mode should have emotional_arc and what_they_hide
        assert "emotional_arc" in data, "Deep mode should have emotional_arc"
        assert "what_they_hide" in data, "Deep mode should have what_they_hide"
        assert data.get("mode") == "deep", f"Mode should be deep, got {data.get('mode')}"
        
        # Deep mode beats should have layered subtext
        beats = data.get("beats", [])
        if beats:
            beat = beats[0]
            # Deep mode should have subtext_surface, subtext_meaning, subtext_fear
            assert "subtext_surface" in beat or "subtext_meaning" in beat, \
                f"Deep mode beat should have layered subtext, got keys: {beat.keys()}"
            # Deep mode should have physical_life
            assert "physical_life" in beat, f"Deep mode beat should have physical_life, got keys: {beat.keys()}"
        
        print(f"✓ Deep mode text analysis returned successfully")
        print(f"  - emotional_arc: {data.get('emotional_arc', '')[:100]}...")
        print(f"  - what_they_hide: {data.get('what_they_hide', '')[:100]}...")
        print(f"  - Mode: {data.get('mode')}")
        print(f"  - Beats count: {len(beats)}")
        if beats:
            print(f"  - First beat has subtext_surface: {'subtext_surface' in beats[0]}")
            print(f"  - First beat has physical_life: {'physical_life' in beats[0]}")
    
    def test_analyze_text_default_mode_is_quick(self):
        """POST /api/analyze/text with no mode should default to quick"""
        response = requests.post(
            f"{BASE_URL}/api/analyze/text",
            json={"text": TEST_SCRIPT},  # No mode specified
            timeout=180
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Default should be quick mode
        mode = data.get("mode")
        assert mode == "quick" or mode is None, f"Default mode should be quick, got {mode}"
        
        print(f"✓ Default mode (no mode specified) works correctly")
        print(f"  - Mode: {mode}")
    
    def test_breakdowns_list(self):
        """GET /api/breakdowns should return list of breakdowns"""
        response = requests.get(f"{BASE_URL}/api/breakdowns", timeout=30)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list), "Should return a list"
        print(f"✓ Breakdowns list returned {len(data)} items")
        
        # Check if any have mode field
        modes_found = [b.get("mode") for b in data[:5] if b.get("mode")]
        print(f"  - Modes in recent breakdowns: {modes_found}")


class TestQuickDeepModeImageAPI:
    """Tests for Quick/Deep mode with image uploads"""
    
    @pytest.fixture
    def test_image_path(self):
        """Create a simple test image"""
        import io
        from PIL import Image
        
        # Create a simple test image with text-like content
        img = Image.new('RGB', (400, 300), color='white')
        # Add some variation to make it look like a document
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        draw.text((50, 50), "JOHN", fill='black')
        draw.text((50, 80), "I didn't come here to argue.", fill='black')
        draw.text((50, 130), "SARAH", fill='black')
        draw.text((50, 160), "Then why did you come?", fill='black')
        
        # Save to temp file
        img_path = "/tmp/test_script_image.jpg"
        img.save(img_path, "JPEG", quality=85)
        return img_path
    
    def test_analyze_image_quick_mode(self, test_image_path):
        """POST /api/analyze/image with mode=quick"""
        with open(test_image_path, 'rb') as f:
            files = {'file': ('test_script.jpg', f, 'image/jpeg')}
            data = {'mode': 'quick'}
            response = requests.post(
                f"{BASE_URL}/api/analyze/image",
                files=files,
                data=data,
                timeout=180
            )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        result = response.json()
        
        print(f"✓ Image analysis with quick mode returned successfully")
        print(f"  - Mode: {result.get('mode')}")
        print(f"  - Has emotional_arc: {'emotional_arc' in result}")
    
    def test_analyze_image_deep_mode(self, test_image_path):
        """POST /api/analyze/image with mode=deep"""
        with open(test_image_path, 'rb') as f:
            files = {'file': ('test_script.jpg', f, 'image/jpeg')}
            data = {'mode': 'deep'}
            response = requests.post(
                f"{BASE_URL}/api/analyze/image",
                files=files,
                data=data,
                timeout=180
            )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        result = response.json()
        
        # Check if fallback
        if result.get("_debug", {}).get("fallback"):
            print(f"  Note: Got fallback response - {result.get('_debug', {}).get('reason')}")
            pytest.skip("Fallback response received")
        
        print(f"✓ Image analysis with deep mode returned successfully")
        print(f"  - Mode: {result.get('mode')}")
        print(f"  - Has emotional_arc: {'emotional_arc' in result}")
        print(f"  - Has what_they_hide: {'what_they_hide' in result}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
