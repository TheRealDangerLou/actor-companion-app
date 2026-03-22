"""
Test suite for Adjustment Loop feature (POST /api/adjust-takes/{breakdown_id})
Tests the new feature that allows actors to refine their acting takes with stacking adjustments.
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAdjustmentLoopFeature:
    """Tests for the Adjustment Loop (adjust-takes) endpoint"""
    
    @pytest.fixture(scope="class")
    def api_client(self):
        """Shared requests session"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        return session
    
    @pytest.fixture(scope="class")
    def existing_breakdown_id(self, api_client):
        """Get an existing breakdown ID from the database"""
        response = api_client.get(f"{BASE_URL}/api/breakdowns")
        assert response.status_code == 200, f"Failed to get breakdowns: {response.text}"
        breakdowns = response.json()
        assert len(breakdowns) > 0, "No breakdowns found in database"
        return breakdowns[0]["id"]
    
    # --- Test: Single adjustment works ---
    def test_adjust_takes_single_adjustment(self, api_client, existing_breakdown_id):
        """POST /api/adjust-takes/{id} with single adjustment returns updated breakdown"""
        response = api_client.post(
            f"{BASE_URL}/api/adjust-takes/{existing_breakdown_id}",
            json={"adjustments": ["tighten_pacing"]}
        )
        
        # Status code assertion
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Data assertions
        data = response.json()
        assert "acting_takes" in data, "Response should contain acting_takes"
        assert "grounded" in data["acting_takes"], "acting_takes should have grounded"
        assert "bold" in data["acting_takes"], "acting_takes should have bold"
        assert "wildcard" in data["acting_takes"], "acting_takes should have wildcard"
        
        # Verify adjustment_history is stored
        assert "adjustment_history" in data, "Response should contain adjustment_history"
        assert len(data["adjustment_history"]) > 0, "adjustment_history should have at least one entry"
        
        # Verify the latest history entry
        latest_history = data["adjustment_history"][-1]
        assert "adjustments" in latest_history, "History entry should have adjustments"
        assert "tighten_pacing" in latest_history["adjustments"], "History should contain tighten_pacing"
        assert "timestamp" in latest_history, "History entry should have timestamp"
        assert "previous_takes" in latest_history, "History entry should have previous_takes"
        
        print(f"✓ Single adjustment (tighten_pacing) applied successfully")
        print(f"  - adjustment_history length: {len(data['adjustment_history'])}")
    
    # --- Test: Multiple stacking adjustments ---
    def test_adjust_takes_stacking_adjustments(self, api_client, existing_breakdown_id):
        """POST /api/adjust-takes/{id} with multiple adjustments applies all"""
        response = api_client.post(
            f"{BASE_URL}/api/adjust-takes/{existing_breakdown_id}",
            json={"adjustments": ["tighten_pacing", "raise_stakes"]}
        )
        
        # Status code assertion
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Data assertions
        data = response.json()
        assert "acting_takes" in data, "Response should contain acting_takes"
        assert "adjustment_history" in data, "Response should contain adjustment_history"
        
        # Verify the latest history entry has both adjustments
        latest_history = data["adjustment_history"][-1]
        assert "tighten_pacing" in latest_history["adjustments"], "History should contain tighten_pacing"
        assert "raise_stakes" in latest_history["adjustments"], "History should contain raise_stakes"
        
        print(f"✓ Stacking adjustments (tighten_pacing + raise_stakes) applied successfully")
    
    # --- Test: All 5 adjustment types ---
    def test_adjust_takes_all_adjustment_types(self, api_client, existing_breakdown_id):
        """POST /api/adjust-takes/{id} accepts all 5 adjustment types"""
        all_adjustments = [
            "tighten_pacing",
            "emotional_depth", 
            "more_natural",
            "raise_stakes",
            "play_opposite"
        ]
        
        response = api_client.post(
            f"{BASE_URL}/api/adjust-takes/{existing_breakdown_id}",
            json={"adjustments": all_adjustments}
        )
        
        # Status code assertion
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Data assertions
        data = response.json()
        assert "acting_takes" in data, "Response should contain acting_takes"
        
        # Verify all adjustments are in history
        latest_history = data["adjustment_history"][-1]
        for adj in all_adjustments:
            assert adj in latest_history["adjustments"], f"History should contain {adj}"
        
        print(f"✓ All 5 adjustment types accepted and applied")
    
    # --- Test: Empty adjustments returns 400 ---
    def test_adjust_takes_empty_adjustments_returns_400(self, api_client, existing_breakdown_id):
        """POST /api/adjust-takes/{id} with empty adjustments returns 400"""
        response = api_client.post(
            f"{BASE_URL}/api/adjust-takes/{existing_breakdown_id}",
            json={"adjustments": []}
        )
        
        # Status code assertion
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        
        # Data assertion - should have error detail
        data = response.json()
        assert "detail" in data, "Error response should have detail"
        
        print(f"✓ Empty adjustments correctly returns 400: {data['detail']}")
    
    # --- Test: Invalid breakdown_id returns 404 ---
    def test_adjust_takes_invalid_id_returns_404(self, api_client):
        """POST /api/adjust-takes/{id} with invalid breakdown_id returns 404"""
        fake_id = "nonexistent-breakdown-id-12345"
        response = api_client.post(
            f"{BASE_URL}/api/adjust-takes/{fake_id}",
            json={"adjustments": ["tighten_pacing"]}
        )
        
        # Status code assertion
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        
        # Data assertion
        data = response.json()
        assert "detail" in data, "Error response should have detail"
        
        print(f"✓ Invalid breakdown_id correctly returns 404: {data['detail']}")
    
    # --- Test: Adjustment history persists across calls ---
    def test_adjustment_history_persists(self, api_client, existing_breakdown_id):
        """Adjustment history accumulates across multiple adjust-takes calls"""
        # First adjustment
        response1 = api_client.post(
            f"{BASE_URL}/api/adjust-takes/{existing_breakdown_id}",
            json={"adjustments": ["more_natural"]}
        )
        assert response1.status_code == 200
        history_len_1 = len(response1.json()["adjustment_history"])
        
        # Second adjustment
        response2 = api_client.post(
            f"{BASE_URL}/api/adjust-takes/{existing_breakdown_id}",
            json={"adjustments": ["play_opposite"]}
        )
        assert response2.status_code == 200
        history_len_2 = len(response2.json()["adjustment_history"])
        
        # History should have grown
        assert history_len_2 > history_len_1, "Adjustment history should accumulate"
        
        # Verify via GET that history persisted
        get_response = api_client.get(f"{BASE_URL}/api/breakdowns/{existing_breakdown_id}")
        assert get_response.status_code == 200
        data = get_response.json()
        assert "adjustment_history" in data, "GET should return adjustment_history"
        assert len(data["adjustment_history"]) == history_len_2, "History should persist in database"
        
        print(f"✓ Adjustment history persists: {history_len_1} -> {history_len_2} entries")


class TestRegenerateTakesRegression:
    """Regression tests to ensure existing regenerate-takes still works"""
    
    @pytest.fixture(scope="class")
    def api_client(self):
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        return session
    
    @pytest.fixture(scope="class")
    def existing_breakdown_id(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/breakdowns")
        assert response.status_code == 200
        breakdowns = response.json()
        assert len(breakdowns) > 0
        return breakdowns[0]["id"]
    
    def test_regenerate_takes_still_works(self, api_client, existing_breakdown_id):
        """POST /api/regenerate-takes/{id} still works (regression)"""
        response = api_client.post(f"{BASE_URL}/api/regenerate-takes/{existing_breakdown_id}")
        
        # Status code assertion
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Data assertions
        data = response.json()
        assert "acting_takes" in data, "Response should contain acting_takes"
        assert "grounded" in data["acting_takes"], "acting_takes should have grounded"
        assert "bold" in data["acting_takes"], "acting_takes should have bold"
        assert "wildcard" in data["acting_takes"], "acting_takes should have wildcard"
        
        # Verify takes have content
        assert len(data["acting_takes"]["grounded"]) > 0, "grounded take should have content"
        assert len(data["acting_takes"]["bold"]) > 0, "bold take should have content"
        assert len(data["acting_takes"]["wildcard"]) > 0, "wildcard take should have content"
        
        print(f"✓ Regenerate takes still works (regression passed)")


class TestBreakdownActingTakesStructure:
    """Tests to verify acting_takes structure in breakdowns"""
    
    @pytest.fixture(scope="class")
    def api_client(self):
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        return session
    
    def test_breakdown_has_acting_takes_tabs(self, api_client):
        """GET /api/breakdowns returns breakdowns with acting_takes (Grounded/Bold/Wildcard)"""
        response = api_client.get(f"{BASE_URL}/api/breakdowns")
        assert response.status_code == 200
        
        breakdowns = response.json()
        assert len(breakdowns) > 0, "Should have at least one breakdown"
        
        # Check first breakdown has proper acting_takes structure
        breakdown = breakdowns[0]
        assert "acting_takes" in breakdown, "Breakdown should have acting_takes"
        
        takes = breakdown["acting_takes"]
        assert "grounded" in takes, "acting_takes should have grounded"
        assert "bold" in takes, "acting_takes should have bold"
        assert "wildcard" in takes, "acting_takes should have wildcard"
        
        print(f"✓ Breakdown has correct acting_takes structure (Grounded/Bold/Wildcard)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
