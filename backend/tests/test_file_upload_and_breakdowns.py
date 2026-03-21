"""
Backend API Tests for Actor's Companion
Tests file upload robustness (MIME type detection, image resizing, error handling)
and the Recent Breakdowns feature.
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test files
TEST_PDF = "/tmp/test_sides.pdf"
TEST_IMAGE = "/tmp/test_sides.jpg"
LARGE_IMAGE = "/tmp/large_test.jpg"


class TestHealthAndBasicEndpoints:
    """Basic API health checks"""
    
    def test_api_root(self):
        """Test API root endpoint"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"✓ API root: {data['message']}")
    
    def test_tts_status(self):
        """Test TTS status endpoint"""
        response = requests.get(f"{BASE_URL}/api/tts/status")
        assert response.status_code == 200
        data = response.json()
        assert "available" in data
        print(f"✓ TTS status: available={data['available']}")


class TestBreakdownsList:
    """Test GET /api/breakdowns - Recent Breakdowns feature"""
    
    def test_list_breakdowns_returns_list(self):
        """GET /api/breakdowns should return a list"""
        response = requests.get(f"{BASE_URL}/api/breakdowns")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ GET /api/breakdowns returned {len(data)} breakdowns")
        
        # Verify structure if there are breakdowns
        if len(data) > 0:
            first = data[0]
            assert "id" in first, "Breakdown should have 'id'"
            assert "created_at" in first, "Breakdown should have 'created_at'"
            print(f"  First breakdown: id={first['id'][:8]}..., character={first.get('character_name', 'N/A')}")


class TestTextAnalysis:
    """Test POST /api/analyze/text - Regression check"""
    
    def test_text_analysis_with_valid_text(self):
        """POST /api/analyze/text with valid text should return 200"""
        test_text = """
        JOHN
        I didn't come here to argue.
        
        SARAH
        Then why did you come?
        
        JOHN
        Because I need you to hear this. Before it's too late.
        """
        
        response = requests.post(
            f"{BASE_URL}/api/analyze/text",
            json={"text": test_text},
            timeout=120
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "id" in data, "Response should have 'id'"
        assert "scene_summary" in data, "Response should have 'scene_summary'"
        assert "character_name" in data, "Response should have 'character_name'"
        assert "beats" in data, "Response should have 'beats'"
        assert "acting_takes" in data, "Response should have 'acting_takes'"
        
        print(f"✓ Text analysis successful: character={data.get('character_name')}")
        return data["id"]
    
    def test_text_analysis_empty_text_returns_400(self):
        """POST /api/analyze/text with empty text should return 400"""
        response = requests.post(
            f"{BASE_URL}/api/analyze/text",
            json={"text": ""},
            timeout=30
        )
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        print(f"✓ Empty text rejected: {data['detail']}")
    
    def test_text_analysis_short_text_returns_400(self):
        """POST /api/analyze/text with too short text should return 400"""
        response = requests.post(
            f"{BASE_URL}/api/analyze/text",
            json={"text": "Hi"},
            timeout=30
        )
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        print(f"✓ Short text rejected: {data['detail']}")


class TestImageAnalysis:
    """Test POST /api/analyze/image - File upload robustness"""
    
    def test_image_upload_with_jpeg(self):
        """POST /api/analyze/image with valid JPEG should return 200"""
        if not os.path.exists(TEST_IMAGE):
            pytest.skip(f"Test image not found: {TEST_IMAGE}")
        
        with open(TEST_IMAGE, "rb") as f:
            files = {"file": ("test_sides.jpg", f, "image/jpeg")}
            response = requests.post(
                f"{BASE_URL}/api/analyze/image",
                files=files,
                timeout=120
            )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "id" in data
        assert "scene_summary" in data or "character_name" in data
        print(f"✓ JPEG upload successful: id={data['id'][:8]}...")
    
    def test_pdf_upload(self):
        """POST /api/analyze/image with valid PDF should return 200"""
        if not os.path.exists(TEST_PDF):
            pytest.skip(f"Test PDF not found: {TEST_PDF}")
        
        with open(TEST_PDF, "rb") as f:
            files = {"file": ("test_sides.pdf", f, "application/pdf")}
            response = requests.post(
                f"{BASE_URL}/api/analyze/image",
                files=files,
                timeout=120
            )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "id" in data
        print(f"✓ PDF upload successful: id={data['id'][:8]}...")
    
    def test_large_image_resizing(self):
        """POST /api/analyze/image with large image (4000px+) should resize and succeed"""
        if not os.path.exists(LARGE_IMAGE):
            pytest.skip(f"Large test image not found: {LARGE_IMAGE}")
        
        with open(LARGE_IMAGE, "rb") as f:
            files = {"file": ("large_test.jpg", f, "image/jpeg")}
            response = requests.post(
                f"{BASE_URL}/api/analyze/image",
                files=files,
                timeout=120
            )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "id" in data
        print(f"✓ Large image upload successful (resized): id={data['id'][:8]}...")
    
    def test_octet_stream_mime_type_detection(self):
        """POST /api/analyze/image with application/octet-stream (iOS edge case) should detect image"""
        if not os.path.exists(TEST_IMAGE):
            pytest.skip(f"Test image not found: {TEST_IMAGE}")
        
        with open(TEST_IMAGE, "rb") as f:
            # Simulate iOS sending application/octet-stream
            files = {"file": ("photo.jpg", f, "application/octet-stream")}
            response = requests.post(
                f"{BASE_URL}/api/analyze/image",
                files=files,
                timeout=120
            )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "id" in data
        print(f"✓ octet-stream MIME type handled correctly: id={data['id'][:8]}...")
    
    def test_empty_mime_type_detection(self):
        """POST /api/analyze/image with empty MIME type (iOS edge case) should detect image"""
        if not os.path.exists(TEST_IMAGE):
            pytest.skip(f"Test image not found: {TEST_IMAGE}")
        
        with open(TEST_IMAGE, "rb") as f:
            # Simulate iOS sending empty content-type
            files = {"file": ("photo.jpg", f, "")}
            response = requests.post(
                f"{BASE_URL}/api/analyze/image",
                files=files,
                timeout=120
            )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "id" in data
        print(f"✓ Empty MIME type handled correctly: id={data['id'][:8]}...")


class TestErrorHandling:
    """Test error handling and descriptive error messages"""
    
    def test_empty_file_returns_400_with_message(self):
        """POST /api/analyze/image with empty file should return 400 with descriptive error"""
        # Create empty file
        empty_content = b""
        files = {"file": ("empty.jpg", empty_content, "image/jpeg")}
        response = requests.post(
            f"{BASE_URL}/api/analyze/image",
            files=files,
            timeout=30
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "detail" in data
        assert len(data["detail"]) > 10, "Error message should be descriptive"
        print(f"✓ Empty file rejected with message: {data['detail']}")
    
    def test_text_file_returns_400_with_message(self):
        """POST /api/analyze/image with text file should return 400 with descriptive error"""
        text_content = b"This is just plain text, not an image or PDF"
        files = {"file": ("notes.txt", text_content, "text/plain")}
        response = requests.post(
            f"{BASE_URL}/api/analyze/image",
            files=files,
            timeout=30
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "detail" in data
        assert len(data["detail"]) > 10, "Error message should be descriptive"
        print(f"✓ Text file rejected with message: {data['detail']}")
    
    def test_invalid_image_bytes_returns_400(self):
        """POST /api/analyze/image with invalid image bytes should return 400"""
        # Random bytes that aren't a valid image
        invalid_content = b"not a valid image file content here"
        files = {"file": ("fake.jpg", invalid_content, "image/jpeg")}
        response = requests.post(
            f"{BASE_URL}/api/analyze/image",
            files=files,
            timeout=30
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "detail" in data
        print(f"✓ Invalid image bytes rejected: {data['detail']}")


class TestBreakdownRetrieval:
    """Test GET /api/breakdowns/{id} - Individual breakdown retrieval"""
    
    def test_get_breakdown_by_id(self):
        """GET /api/breakdowns/{id} should return the breakdown"""
        # First get list to find an existing ID
        list_response = requests.get(f"{BASE_URL}/api/breakdowns")
        if list_response.status_code != 200 or len(list_response.json()) == 0:
            pytest.skip("No existing breakdowns to test retrieval")
        
        breakdown_id = list_response.json()[0]["id"]
        response = requests.get(f"{BASE_URL}/api/breakdowns/{breakdown_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == breakdown_id
        print(f"✓ Retrieved breakdown: id={breakdown_id[:8]}...")
    
    def test_get_nonexistent_breakdown_returns_404(self):
        """GET /api/breakdowns/{id} with invalid ID should return 404"""
        response = requests.get(f"{BASE_URL}/api/breakdowns/nonexistent-id-12345")
        assert response.status_code == 404
        print("✓ Nonexistent breakdown returns 404")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
