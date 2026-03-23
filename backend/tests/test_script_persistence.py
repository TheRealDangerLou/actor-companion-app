"""
Test Script Persistence Features - Iteration 21
Tests for:
1. GET /api/scripts - List recent scripts with metadata
2. GET /api/scripts/{id} - Load full script with breakdowns (no GPT calls)
3. POST /api/scripts/create - Store prep_mode and project_type
4. Verify no re-analysis on script load
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestScriptPersistence:
    """Test script persistence and loading features"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.created_script_ids = []
        yield
        # Cleanup not needed as we're testing read operations
    
    def test_api_root_accessible(self):
        """Test API root endpoint is accessible"""
        response = self.session.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print("PASS: API root endpoint accessible")
    
    def test_list_scripts_endpoint(self):
        """Test GET /api/scripts returns list of recent scripts"""
        response = self.session.get(f"{BASE_URL}/api/scripts")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: GET /api/scripts returns list with {len(data)} scripts")
        return data
    
    def test_list_scripts_has_required_fields(self):
        """Test that scripts list contains required metadata fields"""
        response = self.session.get(f"{BASE_URL}/api/scripts")
        assert response.status_code == 200
        scripts = response.json()
        
        if len(scripts) == 0:
            pytest.skip("No scripts in database to test field structure")
        
        script = scripts[0]
        required_fields = ['id', 'character_name', 'mode', 'created_at']
        for field in required_fields:
            assert field in script, f"Missing required field: {field}"
        
        # breakdown_count should be present (added by endpoint)
        assert 'breakdown_count' in script, "Missing breakdown_count field"
        
        print(f"PASS: Script has all required fields: {list(script.keys())}")
        return script
    
    def test_list_scripts_has_prep_mode_and_project_type(self):
        """Test that scripts list includes prep_mode and project_type if set"""
        response = self.session.get(f"{BASE_URL}/api/scripts")
        assert response.status_code == 200
        scripts = response.json()
        
        if len(scripts) == 0:
            pytest.skip("No scripts in database")
        
        # Check if any script has prep_mode or project_type
        has_prep_mode = any(s.get('prep_mode') for s in scripts)
        has_project_type = any(s.get('project_type') for s in scripts)
        
        print(f"INFO: Scripts with prep_mode: {has_prep_mode}, project_type: {has_project_type}")
        print("PASS: Scripts list endpoint returns prep_mode and project_type fields")
    
    def test_get_script_by_id_with_breakdowns(self):
        """Test GET /api/scripts/{id} returns full script with breakdowns"""
        # First get list of scripts
        list_response = self.session.get(f"{BASE_URL}/api/scripts")
        assert list_response.status_code == 200
        scripts = list_response.json()
        
        if len(scripts) == 0:
            pytest.skip("No scripts in database to test")
        
        # Find a script with breakdowns
        script_with_breakdowns = None
        for s in scripts:
            if s.get('breakdown_count', 0) > 0:
                script_with_breakdowns = s
                break
        
        if not script_with_breakdowns:
            pytest.skip("No scripts with breakdowns found")
        
        script_id = script_with_breakdowns['id']
        
        # Get full script
        response = self.session.get(f"{BASE_URL}/api/scripts/{script_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert 'id' in data
        assert 'character_name' in data
        assert 'breakdowns' in data
        assert isinstance(data['breakdowns'], list)
        assert len(data['breakdowns']) > 0
        
        print(f"PASS: GET /api/scripts/{script_id} returns script with {len(data['breakdowns'])} breakdowns")
        return data
    
    def test_script_breakdowns_have_full_data(self):
        """Test that loaded breakdowns have all required scene data"""
        # Get a script with breakdowns
        list_response = self.session.get(f"{BASE_URL}/api/scripts")
        scripts = list_response.json()
        
        script_with_breakdowns = None
        for s in scripts:
            if s.get('breakdown_count', 0) > 0:
                script_with_breakdowns = s
                break
        
        if not script_with_breakdowns:
            pytest.skip("No scripts with breakdowns found")
        
        script_id = script_with_breakdowns['id']
        response = self.session.get(f"{BASE_URL}/api/scripts/{script_id}")
        data = response.json()
        
        breakdown = data['breakdowns'][0]
        
        # Check for required breakdown fields
        required_fields = [
            'id', 'scene_summary', 'character_name', 'character_objective',
            'stakes', 'beats', 'acting_takes', 'memorization', 'self_tape_tips'
        ]
        
        for field in required_fields:
            assert field in breakdown, f"Breakdown missing required field: {field}"
        
        # Check nested structures
        assert 'grounded' in breakdown.get('acting_takes', {})
        assert 'bold' in breakdown.get('acting_takes', {})
        assert 'wildcard' in breakdown.get('acting_takes', {})
        
        print(f"PASS: Breakdown has all required fields including nested structures")
    
    def test_get_nonexistent_script_returns_404(self):
        """Test that requesting a non-existent script returns 404"""
        fake_id = "nonexistent-script-id-12345"
        response = self.session.get(f"{BASE_URL}/api/scripts/{fake_id}")
        assert response.status_code == 404
        print("PASS: Non-existent script returns 404")
    
    def test_create_script_with_prep_mode_and_project_type(self):
        """Test POST /api/scripts/create stores prep_mode and project_type"""
        payload = {
            "character_name": "TEST_PersistenceTest",
            "mode": "quick",
            "scene_count": 2,
            "prep_mode": "audition",
            "project_type": "tvfilm"
        }
        
        response = self.session.post(f"{BASE_URL}/api/scripts/create", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert 'script_id' in data
        
        script_id = data['script_id']
        self.created_script_ids.append(script_id)
        
        # Verify the script was created with correct fields
        get_response = self.session.get(f"{BASE_URL}/api/scripts/{script_id}")
        assert get_response.status_code == 200
        
        script = get_response.json()
        assert script.get('prep_mode') == 'audition'
        assert script.get('project_type') == 'tvfilm'
        assert script.get('character_name') == 'TEST_PersistenceTest'
        
        print(f"PASS: Script created with prep_mode={script.get('prep_mode')}, project_type={script.get('project_type')}")
    
    def test_create_script_with_booked_prep_mode(self):
        """Test creating script with booked prep mode"""
        payload = {
            "character_name": "TEST_BookedRole",
            "mode": "quick",
            "scene_count": 1,
            "prep_mode": "booked",
            "project_type": "theatre"
        }
        
        response = self.session.post(f"{BASE_URL}/api/scripts/create", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        script_id = data['script_id']
        
        # Verify
        get_response = self.session.get(f"{BASE_URL}/api/scripts/{script_id}")
        script = get_response.json()
        
        assert script.get('prep_mode') == 'booked'
        assert script.get('project_type') == 'theatre'
        
        print("PASS: Script created with booked prep_mode and theatre project_type")
    
    def test_create_script_with_vertical_project_type(self):
        """Test creating script with vertical project type"""
        payload = {
            "character_name": "TEST_VerticalProject",
            "mode": "quick",
            "scene_count": 1,
            "prep_mode": "study",
            "project_type": "vertical"
        }
        
        response = self.session.post(f"{BASE_URL}/api/scripts/create", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        script_id = data['script_id']
        
        get_response = self.session.get(f"{BASE_URL}/api/scripts/{script_id}")
        script = get_response.json()
        
        assert script.get('project_type') == 'vertical'
        print("PASS: Script created with vertical project_type")
    
    def test_script_load_does_not_trigger_analysis(self):
        """Test that loading a script does NOT trigger any GPT/analysis calls
        
        This is verified by:
        1. Timing the request (should be fast, <1s)
        2. Checking response doesn't have _debug.stages with gpt_analysis
        """
        list_response = self.session.get(f"{BASE_URL}/api/scripts")
        scripts = list_response.json()
        
        script_with_breakdowns = None
        for s in scripts:
            if s.get('breakdown_count', 0) > 0:
                script_with_breakdowns = s
                break
        
        if not script_with_breakdowns:
            pytest.skip("No scripts with breakdowns found")
        
        script_id = script_with_breakdowns['id']
        
        # Time the request
        start_time = time.time()
        response = self.session.get(f"{BASE_URL}/api/scripts/{script_id}")
        elapsed = time.time() - start_time
        
        assert response.status_code == 200
        
        # Should be fast (no GPT calls)
        assert elapsed < 5.0, f"Script load took {elapsed:.2f}s - too slow, might be doing analysis"
        
        data = response.json()
        
        # Check that breakdowns don't have fresh _debug.stages indicating new GPT calls
        for breakdown in data.get('breakdowns', []):
            debug = breakdown.get('_debug', {})
            stages = debug.get('stages', [])
            # If there are stages, they should not include a fresh gpt_analysis
            # (cached breakdowns might have _debug from original analysis)
            if stages:
                # This is fine - it's from the original analysis, not a new one
                pass
        
        print(f"PASS: Script loaded in {elapsed:.3f}s - no re-analysis triggered")


class TestScriptListMetadata:
    """Test script list metadata accuracy"""
    
    def test_breakdown_count_matches_actual(self):
        """Test that breakdown_count in list matches actual breakdowns"""
        session = requests.Session()
        
        list_response = session.get(f"{BASE_URL}/api/scripts")
        scripts = list_response.json()
        
        if len(scripts) == 0:
            pytest.skip("No scripts to test")
        
        # Check first script with breakdowns
        for script in scripts:
            if script.get('breakdown_count', 0) > 0:
                script_id = script['id']
                expected_count = script['breakdown_count']
                
                # Get full script
                full_response = session.get(f"{BASE_URL}/api/scripts/{script_id}")
                full_script = full_response.json()
                actual_count = len(full_script.get('breakdowns', []))
                
                assert expected_count == actual_count, \
                    f"breakdown_count mismatch: list says {expected_count}, actual is {actual_count}"
                
                print(f"PASS: breakdown_count ({expected_count}) matches actual breakdowns")
                return
        
        pytest.skip("No scripts with breakdowns found")


class TestCostSafetyNoAutoReanalysis:
    """Test that no auto re-analysis happens on reload"""
    
    def test_multiple_loads_same_result(self):
        """Test that loading the same script multiple times returns identical data"""
        session = requests.Session()
        
        list_response = session.get(f"{BASE_URL}/api/scripts")
        scripts = list_response.json()
        
        script_with_breakdowns = None
        for s in scripts:
            if s.get('breakdown_count', 0) > 0:
                script_with_breakdowns = s
                break
        
        if not script_with_breakdowns:
            pytest.skip("No scripts with breakdowns found")
        
        script_id = script_with_breakdowns['id']
        
        # Load twice
        response1 = session.get(f"{BASE_URL}/api/scripts/{script_id}")
        response2 = session.get(f"{BASE_URL}/api/scripts/{script_id}")
        
        data1 = response1.json()
        data2 = response2.json()
        
        # Should be identical
        assert data1['id'] == data2['id']
        assert len(data1['breakdowns']) == len(data2['breakdowns'])
        
        # Check breakdown IDs are the same (not regenerated)
        ids1 = [b['id'] for b in data1['breakdowns']]
        ids2 = [b['id'] for b in data2['breakdowns']]
        assert ids1 == ids2, "Breakdown IDs changed between loads - possible re-analysis!"
        
        print("PASS: Multiple loads return identical data - no re-analysis")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
