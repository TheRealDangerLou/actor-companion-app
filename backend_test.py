#!/usr/bin/env python3

import requests
import json
import time
import base64
import io
from PIL import Image, ImageDraw
from datetime import datetime

class ActorsCompanionTester:
    def __init__(self):
        self.base_url = "https://script-breakdown-4.preview.emergentagent.com/api"
        self.session = requests.Session()
        self.tests_run = 0
        self.tests_passed = 0
        self.breakdown_ids = []
        
        # Sample script for testing
        self.sample_script = """JOHN
I didn't come here to argue.

SARAH
Then why did you come?

JOHN
Because I need you to hear this. Before it's too late.

SARAH
(pause)
You always say that.

JOHN
This time I mean it."""

    def log_test(self, test_name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {test_name}: PASSED")
        else:
            print(f"❌ {test_name}: FAILED - {details}")
        
        if details:
            print(f"   Details: {details}")
        print()

    def test_health_check(self):
        """Test GET /api/ health check"""
        try:
            response = self.session.get(f"{self.base_url}/", timeout=10)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                expected_msg = "Actor's Companion API"
                if data.get("message") == expected_msg:
                    self.log_test("Health Check", True, f"Status: {response.status_code}, Message: {data.get('message')}")
                else:
                    self.log_test("Health Check", False, f"Unexpected message: {data}")
            else:
                self.log_test("Health Check", False, f"Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test("Health Check", False, f"Exception: {str(e)}")

    def test_text_analysis(self):
        """Test POST /api/analyze/text"""
        try:
            payload = {"text": self.sample_script}
            print(f"📝 Testing text analysis with script length: {len(self.sample_script)} chars")
            print("⏳ This may take 30-60 seconds due to GPT-5.2 processing...")
            
            start_time = time.time()
            response = self.session.post(
                f"{self.base_url}/analyze/text", 
                json=payload, 
                timeout=120
            )
            end_time = time.time()
            processing_time = end_time - start_time
            
            success = response.status_code == 200
            
            if success:
                data = response.json()
                breakdown_id = data.get("id")
                if breakdown_id:
                    self.breakdown_ids.append(breakdown_id)
                
                # Validate required fields
                required_fields = [
                    "id", "scene_summary", "character_name", "character_objective", 
                    "stakes", "beats", "acting_takes", "memorization", "self_tape_tips"
                ]
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    # Validate acting_takes structure
                    acting_takes = data.get("acting_takes", {})
                    take_types = ["grounded", "bold", "wildcard"]
                    missing_takes = [take for take in take_types if take not in acting_takes]
                    
                    if not missing_takes:
                        self.log_test("Text Analysis", True, f"Processing time: {processing_time:.2f}s, ID: {breakdown_id}")
                        return data
                    else:
                        self.log_test("Text Analysis", False, f"Missing acting takes: {missing_takes}")
                else:
                    self.log_test("Text Analysis", False, f"Missing required fields: {missing_fields}")
            else:
                self.log_test("Text Analysis", False, f"Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test("Text Analysis", False, f"Exception: {str(e)}")
            
        return None

    def create_test_image(self):
        """Create a simple test image with text content"""
        try:
            # Create a 800x600 white image
            img = Image.new('RGB', (800, 600), color='white')
            draw = ImageDraw.Draw(img)
            
            # Add script text to the image
            script_lines = [
                "AUDITION SIDES - SCENE 1",
                "",
                "MARY",
                "I can't believe you're leaving.",
                "",
                "TOM", 
                "I don't have a choice.",
                "",
                "MARY",
                "(desperate)",
                "There's always a choice, Tom.",
                "",
                "TOM",
                "Not this time."
            ]
            
            y_position = 50
            for line in script_lines:
                draw.text((50, y_position), line, fill='black')
                y_position += 30
                
            # Convert to bytes
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            return img_buffer.getvalue()
            
        except Exception as e:
            print(f"Error creating test image: {e}")
            return None

    def test_image_analysis(self):
        """Test POST /api/analyze/image"""
        try:
            # Create test image
            image_data = self.create_test_image()
            if not image_data:
                self.log_test("Image Analysis", False, "Could not create test image")
                return None
                
            print(f"📷 Testing image analysis with {len(image_data)} byte image")
            print("⏳ This may take 30-60 seconds due to GPT-5.2 processing...")
            
            files = {'file': ('test_script.png', image_data, 'image/png')}
            
            start_time = time.time()
            response = self.session.post(
                f"{self.base_url}/analyze/image", 
                files=files, 
                timeout=120
            )
            end_time = time.time()
            processing_time = end_time - start_time
            
            success = response.status_code == 200
            
            if success:
                data = response.json()
                breakdown_id = data.get("id")
                if breakdown_id:
                    self.breakdown_ids.append(breakdown_id)
                
                # Validate structure similar to text analysis
                required_fields = [
                    "id", "scene_summary", "character_name", "character_objective", 
                    "stakes", "beats", "acting_takes", "memorization", "self_tape_tips"
                ]
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    self.log_test("Image Analysis", True, f"Processing time: {processing_time:.2f}s, ID: {breakdown_id}")
                    return data
                else:
                    self.log_test("Image Analysis", False, f"Missing required fields: {missing_fields}")
            else:
                self.log_test("Image Analysis", False, f"Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test("Image Analysis", False, f"Exception: {str(e)}")
            
        return None

    def test_get_breakdown(self, breakdown_id):
        """Test GET /api/breakdowns/{id}"""
        if not breakdown_id:
            self.log_test("Get Breakdown", False, "No breakdown ID provided")
            return
            
        try:
            response = self.session.get(f"{self.base_url}/breakdowns/{breakdown_id}", timeout=10)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                if data.get("id") == breakdown_id:
                    self.log_test("Get Breakdown", True, f"Retrieved breakdown {breakdown_id}")
                else:
                    self.log_test("Get Breakdown", False, f"ID mismatch: expected {breakdown_id}, got {data.get('id')}")
            else:
                self.log_test("Get Breakdown", False, f"Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test("Get Breakdown", False, f"Exception: {str(e)}")

    def test_list_breakdowns(self):
        """Test GET /api/breakdowns"""
        try:
            response = self.session.get(f"{self.base_url}/breakdowns", timeout=10)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                if isinstance(data, list):
                    self.log_test("List Breakdowns", True, f"Retrieved {len(data)} breakdowns")
                else:
                    self.log_test("List Breakdowns", False, f"Expected list, got {type(data)}")
            else:
                self.log_test("List Breakdowns", False, f"Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test("List Breakdowns", False, f"Exception: {str(e)}")

    def test_regenerate_takes(self, breakdown_id):
        """Test POST /api/regenerate-takes/{id}"""
        if not breakdown_id:
            self.log_test("Regenerate Takes", False, "No breakdown ID provided")
            return
            
        try:
            print("⏳ Regenerating takes with GPT-5.2...")
            start_time = time.time()
            response = self.session.post(f"{self.base_url}/regenerate-takes/{breakdown_id}", timeout=120)
            end_time = time.time()
            processing_time = end_time - start_time
            
            success = response.status_code == 200
            
            if success:
                data = response.json()
                acting_takes = data.get("acting_takes", {})
                take_types = ["grounded", "bold", "wildcard"]
                
                if all(take_type in acting_takes for take_type in take_types):
                    self.log_test("Regenerate Takes", True, f"Processing time: {processing_time:.2f}s")
                else:
                    missing = [t for t in take_types if t not in acting_takes]
                    self.log_test("Regenerate Takes", False, f"Missing take types: {missing}")
            else:
                self.log_test("Regenerate Takes", False, f"Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test("Regenerate Takes", False, f"Exception: {str(e)}")

    def test_export_pdf(self, breakdown_id):
        """Test GET /api/export-pdf/{id}"""
        if not breakdown_id:
            self.log_test("PDF Export", False, "No breakdown ID provided")
            return
            
        try:
            response = self.session.get(f"{self.base_url}/export-pdf/{breakdown_id}", timeout=30)
            success = response.status_code == 200
            
            if success:
                content_type = response.headers.get('content-type', '')
                if 'application/pdf' in content_type:
                    pdf_size = len(response.content)
                    self.log_test("PDF Export", True, f"PDF size: {pdf_size} bytes")
                else:
                    self.log_test("PDF Export", False, f"Wrong content type: {content_type}")
            else:
                self.log_test("PDF Export", False, f"Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test("PDF Export", False, f"Exception: {str(e)}")

    def test_tts_status(self):
        """Test GET /api/tts/status - should return {available: false} since no API key"""
        try:
            response = self.session.get(f"{self.base_url}/tts/status", timeout=10)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                available = data.get("available")
                # Since ELEVENLABS_API_KEY is empty, should be False
                if available is False:
                    self.log_test("TTS Status", True, f"Available: {available} (correct - no API key)")
                else:
                    self.log_test("TTS Status", False, f"Expected available=false, got {available}")
            else:
                self.log_test("TTS Status", False, f"Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test("TTS Status", False, f"Exception: {str(e)}")

    def test_tts_voices(self):
        """Test GET /api/tts/voices - should return {voices: [], available: false}"""
        try:
            response = self.session.get(f"{self.base_url}/tts/voices", timeout=10)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                voices = data.get("voices", [])
                available = data.get("available")
                
                # Since no API key, should have empty voices and available=false
                if isinstance(voices, list) and len(voices) == 0 and available is False:
                    self.log_test("TTS Voices", True, f"Voices: {len(voices)}, Available: {available} (correct)")
                else:
                    self.log_test("TTS Voices", False, f"Expected empty voices and available=false, got voices={len(voices)}, available={available}")
            else:
                self.log_test("TTS Voices", False, f"Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test("TTS Voices", False, f"Exception: {str(e)}")

    def test_tts_generate(self):
        """Test POST /api/tts/generate - should return 503 when no API key"""
        try:
            payload = {"text": "Hello, this is a test line."}
            response = self.session.post(f"{self.base_url}/tts/generate", json=payload, timeout=15)
            
            # Should return 503 Service Unavailable since no API key
            if response.status_code == 503:
                data = response.json() if response.content else {}
                detail = data.get("detail", "")
                if "ElevenLabs API key" in detail:
                    self.log_test("TTS Generate", True, f"Status: 503, Expected error: {detail}")
                else:
                    self.log_test("TTS Generate", False, f"Status: 503 but unexpected error message: {detail}")
            else:
                self.log_test("TTS Generate", False, f"Expected 503, got {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("TTS Generate", False, f"Exception: {str(e)}")

    def run_all_tests(self):
        """Run complete test suite"""
        print("🎭 Starting Actor's Companion Backend API Tests")
        print(f"🌐 Testing against: {self.base_url}")
        print("="*60)
        
        # Test health check first
        self.test_health_check()
        
        # Test NEW TTS endpoints (key feature to verify)
        print("\n🔊 Testing NEW TTS Endpoints...")
        self.test_tts_status()
        self.test_tts_voices()
        self.test_tts_generate()
        
        # Test text analysis and use the breakdown for dependent tests
        text_breakdown = self.test_text_analysis()
        
        # Test image analysis
        image_breakdown = self.test_image_analysis()
        
        # Test dependent endpoints if we have breakdown IDs
        if self.breakdown_ids:
            primary_id = self.breakdown_ids[0]
            self.test_get_breakdown(primary_id)
            self.test_regenerate_takes(primary_id)
            self.test_export_pdf(primary_id)
        
        # Test list breakdowns
        self.test_list_breakdowns()
        
        # Print summary
        print("="*60)
        print(f"🏁 TEST SUMMARY")
        print(f"📊 Tests Passed: {self.tests_passed}/{self.tests_run}")
        success_rate = (self.tests_passed / self.tests_run) * 100 if self.tests_run > 0 else 0
        print(f"📈 Success Rate: {success_rate:.1f}%")
        print(f"🆔 Created Breakdown IDs: {self.breakdown_ids}")
        
        if success_rate >= 80:
            print("✅ Backend API tests mostly successful!")
        elif success_rate >= 50:
            print("⚠️ Backend API has some issues but is partially functional")
        else:
            print("❌ Backend API has major issues")
            
        return success_rate >= 70

def main():
    tester = ActorsCompanionTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    import sys
    sys.exit(main())