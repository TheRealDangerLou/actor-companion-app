"""
Tests for the new extract-text endpoint and TTS voices endpoint.
Bug fix: Full Script Mode now supports file upload (PDF/image) in addition to text paste.
Also tests Voice Selection for Scene Reader (10 curated voices).
"""
import pytest
import requests
import os
import io
from fpdf import FPDF
from PIL import Image, ImageDraw

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestExtractTextEndpoint:
    """Tests for POST /api/extract-text - extracts text from PDF or image files"""

    def test_extract_text_from_text_pdf(self):
        """Test extracting text from a text-based PDF"""
        # Create a test PDF with script content
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        
        lines = [
            "INT. KITCHEN - DAY",
            "SARAH sits at the table, coffee in hand.",
            "JOHN",
            "We need to talk.",
            "SARAH",
            "About what?",
        ]
        
        for line in lines:
            if line.strip():
                pdf.cell(text=line, new_x="LMARGIN", new_y="NEXT")
        
        pdf_bytes = pdf.output()
        
        # Send to extract-text endpoint
        files = {'file': ('test_script.pdf', io.BytesIO(pdf_bytes), 'application/pdf')}
        response = requests.post(f"{BASE_URL}/api/extract-text", files=files, timeout=30)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "text" in data, "Response should contain 'text' field"
        assert "chars" in data, "Response should contain 'chars' field"
        
        # Verify extracted text contains expected content
        assert "INT. KITCHEN" in data["text"], "Extracted text should contain scene header"
        assert "SARAH" in data["text"], "Extracted text should contain character name"
        assert "We need to talk" in data["text"], "Extracted text should contain dialogue"
        
        # Verify character count
        assert data["chars"] > 50, f"Expected >50 chars, got {data['chars']}"
        assert data["chars"] == len(data["text"]), "chars should match text length"
        
        print(f"✓ PDF text extraction: {data['chars']} characters extracted")

    def test_extract_text_from_image(self):
        """Test extracting text from an image using OCR"""
        # Create a test image with text
        img = Image.new('RGB', (400, 200), color='white')
        draw = ImageDraw.Draw(img)
        draw.text((20, 20), "INT. OFFICE - DAY", fill='black')
        draw.text((20, 50), "MIKE enters the room.", fill='black')
        draw.text((20, 80), "MIKE", fill='black')
        draw.text((20, 110), "Hello everyone.", fill='black')
        
        # Save to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        # Send to extract-text endpoint
        files = {'file': ('test_image.png', img_bytes, 'image/png')}
        response = requests.post(f"{BASE_URL}/api/extract-text", files=files, timeout=60)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "text" in data, "Response should contain 'text' field"
        assert "chars" in data, "Response should contain 'chars' field"
        
        # Verify OCR extracted some text (may not be perfect)
        assert data["chars"] > 10, f"Expected >10 chars from OCR, got {data['chars']}"
        
        print(f"✓ Image OCR extraction: {data['chars']} characters extracted")
        print(f"  Extracted text: {data['text'][:100]}...")

    def test_extract_text_empty_file_returns_400(self):
        """Test that empty file returns 400 error"""
        # Create empty file
        files = {'file': ('empty.pdf', io.BytesIO(b''), 'application/pdf')}
        response = requests.post(f"{BASE_URL}/api/extract-text", files=files, timeout=30)
        
        assert response.status_code == 400, f"Expected 400 for empty file, got {response.status_code}"
        data = response.json()
        assert "detail" in data, "Error response should contain 'detail'"
        assert "empty" in data["detail"].lower(), f"Error should mention 'empty': {data['detail']}"
        
        print(f"✓ Empty file correctly returns 400: {data['detail']}")

    def test_extract_text_unsupported_file_returns_400(self):
        """Test that unsupported file type returns 400 error"""
        # Create a text file (not PDF or image)
        files = {'file': ('test.xyz', io.BytesIO(b'random content'), 'application/octet-stream')}
        response = requests.post(f"{BASE_URL}/api/extract-text", files=files, timeout=30)
        
        # Should return 400 for unsupported type
        assert response.status_code == 400, f"Expected 400 for unsupported file, got {response.status_code}"
        
        print(f"✓ Unsupported file type correctly returns 400")


class TestTTSVoicesEndpoint:
    """Tests for GET /api/tts/voices - returns 10 curated voices"""

    def test_voices_returns_10_voices(self):
        """Test that /api/tts/voices returns exactly 10 voices"""
        response = requests.get(f"{BASE_URL}/api/tts/voices", timeout=10)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "voices" in data, "Response should contain 'voices' field"
        assert "available" in data, "Response should contain 'available' field"
        
        voices = data["voices"]
        assert len(voices) == 10, f"Expected 10 voices, got {len(voices)}"
        
        print(f"✓ /api/tts/voices returns {len(voices)} voices")

    def test_voices_have_full_metadata(self):
        """Test that each voice has complete metadata"""
        response = requests.get(f"{BASE_URL}/api/tts/voices", timeout=10)
        
        assert response.status_code == 200
        data = response.json()
        voices = data["voices"]
        
        required_fields = ["voice_id", "name", "gender", "accent", "style"]
        
        for voice in voices:
            for field in required_fields:
                assert field in voice, f"Voice missing '{field}' field: {voice}"
                assert voice[field], f"Voice '{field}' should not be empty: {voice}"
        
        # Print voice list for verification
        print("✓ All 10 voices have complete metadata:")
        for v in voices:
            print(f"  - {v['name']} ({v['gender']}, {v['accent']}): {v['style']}")

    def test_voices_include_expected_names(self):
        """Test that voices include expected curated names"""
        response = requests.get(f"{BASE_URL}/api/tts/voices", timeout=10)
        
        assert response.status_code == 200
        data = response.json()
        voices = data["voices"]
        
        voice_names = [v["name"] for v in voices]
        
        # Check for some expected voices
        expected_names = ["Rachel", "Adam", "Sarah", "Daniel", "Charlie"]
        for name in expected_names:
            assert name in voice_names, f"Expected voice '{name}' not found in {voice_names}"
        
        print(f"✓ Voices include expected names: {expected_names}")


class TestRegressionPasteSidesFlow:
    """Regression tests to ensure existing paste sides flow still works"""

    def test_analyze_text_quick_mode(self):
        """Test that paste sides with Quick mode still works"""
        script_text = """
JOHN
I didn't come here to argue.

SARAH
Then why did you come?

JOHN
To tell you the truth. Finally.
"""
        response = requests.post(
            f"{BASE_URL}/api/analyze/text",
            json={"text": script_text, "mode": "quick"},
            timeout=120
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify breakdown structure
        assert "id" in data, "Response should contain 'id'"
        assert "scene_summary" in data, "Response should contain 'scene_summary'"
        assert "character_name" in data, "Response should contain 'character_name'"
        assert "beats" in data, "Response should contain 'beats'"
        
        print(f"✓ Paste sides (Quick mode) works: {data.get('character_name', 'Unknown')}")

    def test_full_script_paste_only_flow(self):
        """Test that Full Script paste-only flow still works"""
        script_text = """
INT. KITCHEN - DAY

SARAH sits at the table.

JOHN
We need to talk.

SARAH
About what?

INT. PARKING LOT - NIGHT

JOHN walks to his car.

MIKE
Hey, wait up!

JOHN
Not now, Mike.
"""
        # First parse scenes
        response = requests.post(
            f"{BASE_URL}/api/parse-scenes",
            json={"text": script_text, "character_name": "JOHN"},
            timeout=60
        )
        
        assert response.status_code == 200, f"Parse scenes failed: {response.text}"
        data = response.json()
        
        assert data["total_scenes"] >= 2, f"Expected at least 2 scenes, got {data['total_scenes']}"
        assert data["character_scenes_count"] >= 1, f"Expected JOHN in at least 1 scene"
        
        print(f"✓ Full Script paste-only flow works: {data['total_scenes']} scenes, {data['character_scenes_count']} with JOHN")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
