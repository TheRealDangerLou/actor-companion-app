"""
Test suite for scanned PDF fix - validates the pymupdf-based PDF-to-image rendering
for image-based PDFs that have no selectable text.

Test files:
- /tmp/scanned_sides.pdf - Image-based PDF with no selectable text (critical test)
- /tmp/text_sides.pdf - Text-based PDF (regression test)
- /tmp/test_sides.jpg - JPEG image (regression test)
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestDebugPipeline:
    """Test the debug pipeline endpoint for pymupdf support"""
    
    def test_debug_pipeline_all_ok(self):
        """GET /api/debug/pipeline should show all stages ok including pdf_image_support"""
        response = requests.get(f"{BASE_URL}/api/debug/pipeline", timeout=30)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("all_ok") == True, f"Expected all_ok=True, got {data}"
        
        stages = data.get("stages", {})
        
        # Check pdf_text_support (PyPDF2)
        assert "pdf_text_support" in stages, "Missing pdf_text_support stage"
        assert stages["pdf_text_support"]["ok"] == True, f"pdf_text_support not ok: {stages['pdf_text_support']}"
        
        # Check pdf_image_support (pymupdf) - critical for scanned PDFs
        assert "pdf_image_support" in stages, "Missing pdf_image_support stage"
        assert stages["pdf_image_support"]["ok"] == True, f"pdf_image_support not ok: {stages['pdf_image_support']}"
        assert "pymupdf_version" in stages["pdf_image_support"], "Missing pymupdf_version"
        print(f"✓ pdf_image_support ok with pymupdf version: {stages['pdf_image_support']['pymupdf_version']}")


class TestScannedPDFUpload:
    """Test scanned/image-based PDF upload - the critical fix"""
    
    def test_scanned_pdf_upload_succeeds(self):
        """POST /api/analyze/image with scanned PDF should succeed via vision OCR path"""
        pdf_path = "/tmp/scanned_sides.pdf"
        
        if not os.path.exists(pdf_path):
            pytest.skip(f"Test file not found: {pdf_path}")
        
        with open(pdf_path, 'rb') as f:
            files = {'file': ('scanned_sides.pdf', f, 'application/pdf')}
            data = {'mode': 'quick'}
            
            print(f"Uploading scanned PDF ({os.path.getsize(pdf_path) / 1024:.0f}KB)...")
            response = requests.post(
                f"{BASE_URL}/api/analyze/image",
                files=files,
                data=data,
                timeout=120  # GPT calls take 15-30s
            )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:500]}"
        
        result = response.json()
        
        # Check debug stages
        debug = result.get("_debug", {})
        stages = debug.get("stages", [])
        stage_names = [s.get("stage") for s in stages]
        
        print(f"Stages: {stage_names}")
        
        # Expected flow for scanned PDF:
        # file_received -> type_detection -> pdf_extract (0 chars) -> pdf_text_check (fail) -> pdf_to_images (ok) -> gpt_vision (ok) -> db_save (ok)
        
        assert "file_received" in stage_names, "Missing file_received stage"
        assert "type_detection" in stage_names, "Missing type_detection stage"
        assert "pdf_extract" in stage_names, "Missing pdf_extract stage"
        
        # Check pdf_extract shows minimal text
        pdf_extract_stage = next((s for s in stages if s.get("stage") == "pdf_extract"), None)
        assert pdf_extract_stage is not None, "pdf_extract stage not found"
        chars_extracted = pdf_extract_stage.get("chars", 0)
        print(f"PDF text extraction: {chars_extracted} chars")
        
        # For scanned PDF, should have very little text
        if chars_extracted < 10:
            # Should have gone through pdf_to_images path
            assert "pdf_text_check" in stage_names, "Missing pdf_text_check stage (expected for scanned PDF)"
            assert "pdf_to_images" in stage_names, "Missing pdf_to_images stage (critical for scanned PDF)"
            
            # Check pdf_to_images stage
            pdf_to_images_stage = next((s for s in stages if s.get("stage") == "pdf_to_images"), None)
            assert pdf_to_images_stage is not None, "pdf_to_images stage not found"
            assert pdf_to_images_stage.get("ok") == True, f"pdf_to_images failed: {pdf_to_images_stage}"
            pages_rendered = pdf_to_images_stage.get("pages_rendered", 0)
            assert pages_rendered >= 1, f"Expected at least 1 page rendered, got {pages_rendered}"
            print(f"✓ pdf_to_images rendered {pages_rendered} page(s)")
            
            # Should use gpt_vision (not gpt_analysis)
            assert "gpt_vision" in stage_names, "Missing gpt_vision stage (expected for scanned PDF)"
        
        # Check db_save
        assert "db_save" in stage_names, "Missing db_save stage"
        
        # Check result has valid breakdown structure
        assert "id" in result, "Missing id in result"
        assert "scene_summary" in result, "Missing scene_summary in result"
        assert "character_name" in result, "Missing character_name in result"
        
        # Check it's not a fallback response
        assert debug.get("fallback") != True, f"Got fallback response: {debug.get('reason')}"
        
        print(f"✓ Scanned PDF analysis succeeded")
        print(f"  Character: {result.get('character_name')}")
        print(f"  Summary: {result.get('scene_summary', '')[:100]}...")


class TestTextBasedPDFUpload:
    """Test text-based PDF upload - regression test for fast path"""
    
    def test_text_pdf_uses_fast_path(self):
        """POST /api/analyze/image with text-based PDF should use fast path (no vision)"""
        pdf_path = "/tmp/text_sides.pdf"
        
        if not os.path.exists(pdf_path):
            pytest.skip(f"Test file not found: {pdf_path}")
        
        with open(pdf_path, 'rb') as f:
            files = {'file': ('text_sides.pdf', f, 'application/pdf')}
            data = {'mode': 'quick'}
            
            print(f"Uploading text-based PDF ({os.path.getsize(pdf_path) / 1024:.0f}KB)...")
            response = requests.post(
                f"{BASE_URL}/api/analyze/image",
                files=files,
                data=data,
                timeout=120
            )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:500]}"
        
        result = response.json()
        debug = result.get("_debug", {})
        stages = debug.get("stages", [])
        stage_names = [s.get("stage") for s in stages]
        
        print(f"Stages: {stage_names}")
        
        # For text-based PDF, should NOT go through pdf_to_images
        # Expected: file_received -> type_detection -> pdf_extract -> gpt_analysis -> db_save
        
        assert "pdf_extract" in stage_names, "Missing pdf_extract stage"
        
        pdf_extract_stage = next((s for s in stages if s.get("stage") == "pdf_extract"), None)
        chars_extracted = pdf_extract_stage.get("chars", 0)
        print(f"PDF text extraction: {chars_extracted} chars")
        
        if chars_extracted >= 10:
            # Should use fast path (gpt_analysis, not gpt_vision)
            assert "gpt_analysis" in stage_names, "Missing gpt_analysis stage (expected for text PDF)"
            assert "pdf_to_images" not in stage_names, "Unexpected pdf_to_images stage for text PDF"
            assert "gpt_vision" not in stage_names, "Unexpected gpt_vision stage for text PDF"
            print(f"✓ Text PDF used fast path (gpt_analysis)")
        
        assert debug.get("fallback") != True, f"Got fallback response: {debug.get('reason')}"
        print(f"✓ Text-based PDF analysis succeeded")


class TestJPEGUpload:
    """Test JPEG image upload - regression test"""
    
    def test_jpeg_upload_succeeds(self):
        """POST /api/analyze/image with JPEG should still work"""
        jpg_path = "/tmp/test_sides.jpg"
        
        if not os.path.exists(jpg_path):
            pytest.skip(f"Test file not found: {jpg_path}")
        
        with open(jpg_path, 'rb') as f:
            files = {'file': ('test_sides.jpg', f, 'image/jpeg')}
            data = {'mode': 'quick'}
            
            print(f"Uploading JPEG ({os.path.getsize(jpg_path) / 1024:.0f}KB)...")
            response = requests.post(
                f"{BASE_URL}/api/analyze/image",
                files=files,
                data=data,
                timeout=120
            )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:500]}"
        
        result = response.json()
        debug = result.get("_debug", {})
        stages = debug.get("stages", [])
        stage_names = [s.get("stage") for s in stages]
        
        print(f"Stages: {stage_names}")
        
        # Expected: file_received -> type_detection -> image_convert -> gpt_vision -> db_save
        assert "image_convert" in stage_names, "Missing image_convert stage"
        assert "gpt_vision" in stage_names, "Missing gpt_vision stage"
        assert "db_save" in stage_names, "Missing db_save stage"
        
        assert debug.get("fallback") != True, f"Got fallback response: {debug.get('reason')}"
        print(f"✓ JPEG upload succeeded")


class TestOctetStreamMIME:
    """Test application/octet-stream MIME type handling"""
    
    def test_octet_stream_jpeg_detected(self):
        """POST /api/analyze/image with application/octet-stream MIME should detect and process correctly"""
        jpg_path = "/tmp/test_sides.jpg"
        
        if not os.path.exists(jpg_path):
            pytest.skip(f"Test file not found: {jpg_path}")
        
        with open(jpg_path, 'rb') as f:
            # Send with generic MIME type (like iOS sometimes does)
            files = {'file': ('test_sides.jpg', f, 'application/octet-stream')}
            data = {'mode': 'quick'}
            
            print("Uploading JPEG with application/octet-stream MIME...")
            response = requests.post(
                f"{BASE_URL}/api/analyze/image",
                files=files,
                data=data,
                timeout=120
            )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:500]}"
        
        result = response.json()
        debug = result.get("_debug", {})
        stages = debug.get("stages", [])
        
        # Check type detection worked
        type_detection = next((s for s in stages if s.get("stage") == "type_detection"), None)
        assert type_detection is not None, "Missing type_detection stage"
        assert type_detection.get("detected") == "image", f"Expected detected=image, got {type_detection}"
        
        assert debug.get("fallback") != True, f"Got fallback response: {debug.get('reason')}"
        print(f"✓ application/octet-stream MIME handled correctly")


class TestTextAnalysis:
    """Test text analysis endpoint - regression test"""
    
    def test_text_analysis_quick_mode(self):
        """POST /api/analyze/text with mode=quick should still work"""
        test_text = """JOHN
I didn't come here to argue.

SARAH
Then why did you come?

JOHN
You know why. I came to say goodbye.
"""
        
        response = requests.post(
            f"{BASE_URL}/api/analyze/text",
            json={"text": test_text, "mode": "quick"},
            timeout=120
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:500]}"
        
        result = response.json()
        
        # Check basic structure
        assert "id" in result, "Missing id"
        assert "scene_summary" in result, "Missing scene_summary"
        assert "character_name" in result, "Missing character_name"
        assert "beats" in result, "Missing beats"
        assert "acting_takes" in result, "Missing acting_takes"
        
        debug = result.get("_debug", {})
        assert debug.get("fallback") != True, f"Got fallback response: {debug.get('reason')}"
        
        print(f"✓ Text analysis (quick mode) succeeded")
        print(f"  Character: {result.get('character_name')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
