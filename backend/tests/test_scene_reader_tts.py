"""
Test Scene Reader TTS (Text-to-Speech) functionality
Tests the /api/tts/generate endpoint used by the Scene Reader feature
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestTTSEndpoint:
    """Tests for the TTS generate endpoint used by Scene Reader"""
    
    def test_tts_status_endpoint(self):
        """Test that TTS status endpoint returns availability info"""
        response = requests.get(f"{BASE_URL}/api/tts/status")
        assert response.status_code == 200
        data = response.json()
        assert "available" in data
        print(f"TTS available: {data['available']}")
    
    def test_tts_generate_success(self):
        """Test TTS generation with valid text"""
        response = requests.post(
            f"{BASE_URL}/api/tts/generate",
            json={"text": "Hello, this is a test."},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()
        assert "audio_url" in data
        # Verify it's a base64 data URI
        assert data["audio_url"].startswith("data:audio/mpeg;base64,")
        # Verify there's actual audio data
        audio_data = data["audio_url"].split(",")[1]
        assert len(audio_data) > 100  # Should have substantial audio data
        print(f"TTS generated audio: {len(audio_data)} base64 chars")
    
    def test_tts_generate_empty_text_fails(self):
        """Test that empty text returns 400 error"""
        response = requests.post(
            f"{BASE_URL}/api/tts/generate",
            json={"text": ""},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        print(f"Empty text error: {data['detail']}")
    
    def test_tts_generate_whitespace_only_fails(self):
        """Test that whitespace-only text returns 400 error"""
        response = requests.post(
            f"{BASE_URL}/api/tts/generate",
            json={"text": "   "},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        assert response.status_code == 400
    
    def test_tts_generate_with_custom_voice_id(self):
        """Test TTS generation with custom voice_id parameter"""
        response = requests.post(
            f"{BASE_URL}/api/tts/generate",
            json={
                "text": "Testing custom voice.",
                "voice_id": "21m00Tcm4TlvDq8ikWAM"  # Default ElevenLabs voice
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()
        assert "audio_url" in data
        assert data["audio_url"].startswith("data:audio/mpeg;base64,")
    
    def test_tts_voices_endpoint(self):
        """Test that voices endpoint returns list of available voices"""
        response = requests.get(f"{BASE_URL}/api/tts/voices")
        assert response.status_code == 200
        data = response.json()
        assert "voices" in data
        assert "available" in data
        if data["available"]:
            assert isinstance(data["voices"], list)
            print(f"Available voices: {len(data['voices'])}")


class TestBreakdownsForSceneReader:
    """Tests to verify breakdowns have memorization data for Scene Reader"""
    
    def test_breakdown_has_memorization_data(self):
        """Test that breakdowns include cue_recall data for Scene Reader"""
        # Get list of breakdowns
        response = requests.get(f"{BASE_URL}/api/breakdowns")
        assert response.status_code == 200
        breakdowns = response.json()
        assert len(breakdowns) > 0, "No breakdowns available for testing"
        
        # Check first breakdown has memorization data
        breakdown_id = breakdowns[0]["id"]
        response = requests.get(f"{BASE_URL}/api/breakdowns/{breakdown_id}")
        assert response.status_code == 200
        breakdown = response.json()
        
        # Verify memorization structure
        assert "memorization" in breakdown
        memorization = breakdown["memorization"]
        assert "cue_recall" in memorization
        cue_recall = memorization["cue_recall"]
        
        # Verify cue_recall has items
        assert isinstance(cue_recall, list)
        if len(cue_recall) > 0:
            # Verify structure of cue_recall items
            first_cue = cue_recall[0]
            assert "cue" in first_cue
            assert "your_line" in first_cue
            print(f"Breakdown has {len(cue_recall)} cue/line pairs for Scene Reader")
        else:
            print("Warning: Breakdown has empty cue_recall")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
