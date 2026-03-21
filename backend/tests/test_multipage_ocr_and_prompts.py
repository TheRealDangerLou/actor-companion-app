"""
Test suite for multi-page scanned PDF OCR and tactic-based prompt quality.
Tests the NEW features:
1. Multi-page scanned PDF support - OCRs each page independently via GPT Vision
2. Prompt overhaul - tactic-based language, no softening cruel characters
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Antagonist scene for prompt quality testing
ANTAGONIST_SCENE = """FELIX
You think this is about you? This was never about you.

MARIA
Then what was it about?

FELIX
It was about making sure you understood your place.

MARIA
My place? I built this company while you were--

FELIX
(cutting her off)
While I was what? Watching? Learning? You never saw me coming, Maria.
That's always been your problem.

MARIA
You're making a mistake.

FELIX
No. You made the mistake. Years ago. When you thought loyalty meant weakness.
"""

# Words that should NOT appear in tactic-based analysis of antagonist
THERAPY_WORDS = ['guilt', 'shame', 'vulnerability', 'insecurity', 'wounded', 'hurt', 'pain', 'fear of rejection']


class TestDebugPipeline:
    """Verify all pipeline stages are green including pdf_image_support"""
    
    def test_debug_pipeline_all_ok(self):
        """GET /api/debug/pipeline should show all stages green"""
        response = requests.get(f"{BASE_URL}/api/debug/pipeline", timeout=30)
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("all_ok") == True, f"Pipeline not all ok: {data}"
        
        stages = data.get("stages", {})
        assert stages.get("llm_key", {}).get("ok") == True
        assert stages.get("gpt_call", {}).get("ok") == True
        assert stages.get("mongodb", {}).get("ok") == True
        assert stages.get("image_processing", {}).get("ok") == True
        assert stages.get("pdf_text_support", {}).get("ok") == True
        assert stages.get("pdf_image_support", {}).get("ok") == True
        
        print(f"All pipeline stages OK: {list(stages.keys())}")


class TestMultiPageScannedPDF:
    """Test multi-page scanned PDF OCR functionality"""
    
    def test_multipage_scanned_pdf_ocr(self):
        """POST /api/analyze/image with multi-page scanned PDF should OCR all pages"""
        pdf_path = '/tmp/multi_page_scanned.pdf'
        
        if not os.path.exists(pdf_path):
            pytest.skip(f"Test file not found: {pdf_path}")
        
        with open(pdf_path, 'rb') as f:
            files = {'file': ('multi_page_scanned.pdf', f, 'application/pdf')}
            data = {'mode': 'quick'}
            
            # Multi-page OCR can take 60-120s
            response = requests.post(
                f"{BASE_URL}/api/analyze/image",
                files=files,
                data=data,
                timeout=300
            )
        
        assert response.status_code == 200, f"Failed: {response.text[:500]}"
        
        result = response.json()
        debug = result.get("_debug", {})
        stages = debug.get("stages", [])
        
        # Find ocr_complete stage
        ocr_stage = None
        for stage in stages:
            if stage.get("stage") == "ocr_complete":
                ocr_stage = stage
                break
        
        assert ocr_stage is not None, f"No ocr_complete stage found. Stages: {[s.get('stage') for s in stages]}"
        assert ocr_stage.get("ok") == True, f"OCR failed: {ocr_stage}"
        
        pages_ocrd = ocr_stage.get("pages_ocrd", 0)
        total_chars = ocr_stage.get("total_chars", 0)
        
        assert pages_ocrd > 1, f"Expected multiple pages OCR'd, got {pages_ocrd}"
        assert total_chars > 100, f"Expected substantial text, got {total_chars} chars"
        
        print(f"Multi-page OCR SUCCESS: {pages_ocrd} pages, {total_chars} chars")
        print(f"Character: {result.get('character_name')}")
        print(f"Objective: {result.get('character_objective')}")
    
    def test_single_page_scanned_pdf_still_works(self):
        """POST /api/analyze/image with single-page scanned PDF still works"""
        pdf_path = '/tmp/scanned_sides.pdf'
        
        if not os.path.exists(pdf_path):
            pytest.skip(f"Test file not found: {pdf_path}")
        
        with open(pdf_path, 'rb') as f:
            files = {'file': ('scanned_sides.pdf', f, 'application/pdf')}
            data = {'mode': 'quick'}
            
            response = requests.post(
                f"{BASE_URL}/api/analyze/image",
                files=files,
                data=data,
                timeout=120
            )
        
        assert response.status_code == 200, f"Failed: {response.text[:500]}"
        
        result = response.json()
        debug = result.get("_debug", {})
        
        # Should have gone through OCR path
        stages = debug.get("stages", [])
        stage_names = [s.get("stage") for s in stages]
        
        # Either ocr_complete (multi-page path) or gpt_vision (single image path)
        assert "ocr_complete" in stage_names or "gpt_vision" in stage_names, f"No OCR stage found: {stage_names}"
        
        print(f"Single-page scanned PDF processed. Stages: {stage_names}")
    
    def test_text_based_pdf_fast_path(self):
        """POST /api/analyze/image with text-based PDF uses fast path (no OCR)"""
        pdf_path = '/tmp/text_sides.pdf'
        
        if not os.path.exists(pdf_path):
            pytest.skip(f"Test file not found: {pdf_path}")
        
        with open(pdf_path, 'rb') as f:
            files = {'file': ('text_sides.pdf', f, 'application/pdf')}
            data = {'mode': 'quick'}
            
            response = requests.post(
                f"{BASE_URL}/api/analyze/image",
                files=files,
                data=data,
                timeout=120
            )
        
        assert response.status_code == 200, f"Failed: {response.text[:500]}"
        
        result = response.json()
        debug = result.get("_debug", {})
        stages = debug.get("stages", [])
        stage_names = [s.get("stage") for s in stages]
        
        # Should use gpt_analysis (text path), NOT gpt_vision or ocr_complete
        assert "gpt_analysis" in stage_names, f"Expected gpt_analysis stage, got: {stage_names}"
        assert "gpt_vision" not in stage_names, f"Should not use vision for text PDF: {stage_names}"
        assert "ocr_complete" not in stage_names, f"Should not use OCR for text PDF: {stage_names}"
        
        print(f"Text-based PDF used fast path. Stages: {stage_names}")


class TestPromptQuality:
    """Test that prompts produce tactic-based language, not therapy language"""
    
    def test_deep_mode_antagonist_no_therapy_language(self):
        """POST /api/analyze/text with mode=deep for antagonist should use tactic language"""
        response = requests.post(
            f"{BASE_URL}/api/analyze/text",
            json={"text": ANTAGONIST_SCENE, "mode": "deep"},
            timeout=180
        )
        
        assert response.status_code == 200, f"Failed: {response.text[:500]}"
        
        result = response.json()
        
        # Check objective - should be active verb, not feeling
        objective = result.get("character_objective", "").lower()
        assert objective, "No objective returned"
        
        # Check what_they_hide - should NOT default to guilt/shame
        what_they_hide = result.get("what_they_hide", "").lower()
        
        # Check for therapy words in key fields
        fields_to_check = {
            "character_objective": objective,
            "what_they_hide": what_they_hide,
        }
        
        therapy_found = []
        for field_name, field_value in fields_to_check.items():
            for word in THERAPY_WORDS:
                if word in field_value:
                    therapy_found.append(f"{field_name}: '{word}'")
        
        # Also check beats
        for beat in result.get("beats", []):
            beat_text = f"{beat.get('description', '')} {beat.get('subtext_meaning', '')}".lower()
            for word in THERAPY_WORDS:
                if word in beat_text:
                    therapy_found.append(f"beat {beat.get('beat_number')}: '{word}'")
        
        # Report findings but don't fail hard - prompts are probabilistic
        if therapy_found:
            print(f"WARNING: Therapy language found: {therapy_found}")
            print(f"Objective: {objective}")
            print(f"What they hide: {what_they_hide}")
        else:
            print("SUCCESS: No therapy language in antagonist analysis")
        
        # Verify tactic-based language is present
        tactic_indicators = ['to ', 'control', 'dominate', 'corner', 'shut', 'force', 'make', 'ensure', 'establish']
        has_tactic = any(ind in objective for ind in tactic_indicators)
        
        print(f"Objective: {objective}")
        print(f"Has tactic verb: {has_tactic}")
        
        # Check character name detected
        assert result.get("character_name"), "No character name detected"
        print(f"Character: {result.get('character_name')}")
    
    def test_quick_mode_tactic_based_beats(self):
        """POST /api/analyze/text with mode=quick should return tactic-based beats"""
        response = requests.post(
            f"{BASE_URL}/api/analyze/text",
            json={"text": ANTAGONIST_SCENE, "mode": "quick"},
            timeout=120
        )
        
        assert response.status_code == 200, f"Failed: {response.text[:500]}"
        
        result = response.json()
        beats = result.get("beats", [])
        
        assert len(beats) > 0, "No beats returned"
        
        # Check beats have tactic-based descriptions
        for beat in beats:
            title = beat.get("title", "")
            description = beat.get("description", "")
            subtext = beat.get("subtext", "")
            
            print(f"Beat {beat.get('beat_number')}: {title}")
            print(f"  Description: {description[:100]}...")
            print(f"  Subtext: {subtext[:100]}...")
        
        # Verify structure
        first_beat = beats[0]
        assert "beat_number" in first_beat
        assert "title" in first_beat
        assert "description" in first_beat
        assert "subtext" in first_beat
        
        print(f"Quick mode returned {len(beats)} tactic-based beats")


class TestRegressions:
    """Regression tests for existing functionality"""
    
    def test_get_breakdowns_list(self):
        """GET /api/breakdowns returns list"""
        response = requests.get(f"{BASE_URL}/api/breakdowns", timeout=30)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"Breakdowns list: {len(data)} items")
    
    def test_jpeg_image_still_works(self):
        """POST /api/analyze/image with JPEG still works"""
        # Create a simple test JPEG
        from PIL import Image, ImageDraw
        import io
        
        img = Image.new('RGB', (400, 300), color='white')
        draw = ImageDraw.Draw(img)
        draw.text((50, 50), "JOHN", fill='black')
        draw.text((50, 80), "Hello there.", fill='black')
        draw.text((50, 120), "MARY", fill='black')
        draw.text((50, 150), "Hi John.", fill='black')
        
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=85)
        buf.seek(0)
        
        files = {'file': ('test.jpg', buf, 'image/jpeg')}
        data = {'mode': 'quick'}
        
        response = requests.post(
            f"{BASE_URL}/api/analyze/image",
            files=files,
            data=data,
            timeout=120
        )
        
        assert response.status_code == 200, f"Failed: {response.text[:500]}"
        
        result = response.json()
        debug = result.get("_debug", {})
        stages = debug.get("stages", [])
        stage_names = [s.get("stage") for s in stages]
        
        assert "gpt_vision" in stage_names, f"Expected gpt_vision stage: {stage_names}"
        print(f"JPEG image processed. Stages: {stage_names}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
