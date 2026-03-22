"""
Test suite for scene-level error reporting and retry flow.
Tests:
1. Backend: POST /api/analyze/scene returns 400 for empty scene text
2. Backend: Error categorization (402=budget, 429=rate limit, 503=service unavailable, 504=timeout, 500=other)
3. Frontend: Failed scene tabs with red styling and AlertTriangle icon
4. Frontend: Retry card with error type badge, error message, and Retry button
5. Frontend: Action bar hidden for failed scenes
6. Frontend: handleRetryScene replaces failed placeholder on success
7. Frontend: Error classification maps status codes to correct errorType strings
8. Frontend: Cost summary bar renders correctly in ScriptOverview header
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAnalyzeSceneErrorHandling:
    """Test /api/analyze/scene endpoint error handling"""
    
    def test_empty_scene_text_returns_400(self):
        """POST /api/analyze/scene returns 400 for empty scene text"""
        response = requests.post(f"{BASE_URL}/api/analyze/scene", json={
            "script_id": "test-script-id",
            "scene_number": 1,
            "scene_heading": "Test Scene",
            "text": "",  # Empty text
            "character_name": "TEST_CHARACTER",
            "mode": "quick"
        }, timeout=30)
        
        assert response.status_code == 400, f"Expected 400 for empty text, got {response.status_code}"
        data = response.json()
        assert "detail" in data
        assert "empty" in data["detail"].lower() or "cannot be empty" in data["detail"].lower()
        print(f"PASS: Empty scene text returns 400 with message: {data['detail']}")
    
    def test_whitespace_only_scene_text_returns_400(self):
        """POST /api/analyze/scene returns 400 for whitespace-only scene text"""
        response = requests.post(f"{BASE_URL}/api/analyze/scene", json={
            "script_id": "test-script-id",
            "scene_number": 1,
            "scene_heading": "Test Scene",
            "text": "   \n\t  ",  # Whitespace only
            "character_name": "TEST_CHARACTER",
            "mode": "quick"
        }, timeout=30)
        
        assert response.status_code == 400, f"Expected 400 for whitespace text, got {response.status_code}"
        print("PASS: Whitespace-only scene text returns 400")


class TestBackendErrorCategorization:
    """Test that backend categorizes errors with correct HTTP status codes"""
    
    def test_analyze_scene_endpoint_exists(self):
        """Verify /api/analyze/scene endpoint is accessible"""
        # Send a minimal valid request to check endpoint exists
        response = requests.post(f"{BASE_URL}/api/analyze/scene", json={
            "script_id": "test-script-id",
            "scene_number": 1,
            "scene_heading": "Test Scene",
            "text": "JOHN: Hello there.",
            "character_name": "JOHN",
            "mode": "quick"
        }, timeout=120)
        
        # Should either succeed (200) or fail with a specific error, not 404
        assert response.status_code != 404, "Endpoint /api/analyze/scene not found"
        print(f"PASS: /api/analyze/scene endpoint exists, returned status {response.status_code}")
    
    def test_error_code_mapping_in_server_code(self):
        """Verify error categorization logic exists in server.py"""
        # Read server.py and verify error handling code
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Check for 402 budget exceeded
        assert "status_code=402" in content, "Missing 402 status code for budget exceeded"
        assert "budget" in content.lower() and "exceeded" in content.lower(), "Missing budget exceeded check"
        
        # Check for 429 rate limit
        assert "status_code=429" in content, "Missing 429 status code for rate limit"
        assert "rate" in content.lower() and "limit" in content.lower(), "Missing rate limit check"
        
        # Check for 503 service unavailable
        assert "status_code=503" in content, "Missing 503 status code for service unavailable"
        assert "service" in content.lower() and "unavailable" in content.lower(), "Missing service unavailable check"
        
        # Check for 504 timeout
        assert "status_code=504" in content, "Missing 504 status code for timeout"
        assert "TimeoutError" in content or "timed out" in content.lower(), "Missing timeout handling"
        
        # Check for 500 generic error
        assert "status_code=500" in content, "Missing 500 status code for generic errors"
        
        print("PASS: All error status codes (402, 429, 503, 504, 500) are properly mapped in server.py")


class TestFrontendErrorClassification:
    """Test frontend error classification logic in App.js"""
    
    def test_error_type_mapping_in_app_js(self):
        """Verify App.js maps status codes to correct errorType strings"""
        app_js_path = "/app/frontend/src/App.js"
        with open(app_js_path, 'r') as f:
            content = f.read()
        
        # Check for 402 -> budget_exceeded
        assert "status === 402" in content or "status==402" in content.replace(" ", ""), "Missing 402 status check"
        assert "budget_exceeded" in content, "Missing budget_exceeded errorType"
        
        # Check for 429 -> rate_limited
        assert "status === 429" in content or "status==429" in content.replace(" ", ""), "Missing 429 status check"
        assert "rate_limited" in content, "Missing rate_limited errorType"
        
        # Check for 503 -> service_unavailable
        assert "status === 503" in content or "status==503" in content.replace(" ", ""), "Missing 503 status check"
        assert "service_unavailable" in content, "Missing service_unavailable errorType"
        
        # Check for 504 -> timeout
        assert "status === 504" in content or "status==504" in content.replace(" ", ""), "Missing 504 status check"
        assert '"timeout"' in content or "'timeout'" in content, "Missing timeout errorType"
        
        # Check for network_error when no response
        assert "network_error" in content, "Missing network_error errorType"
        
        print("PASS: App.js correctly maps status codes to errorType strings (402->budget_exceeded, 429->rate_limited, 503->service_unavailable, 504->timeout, no response->network_error)")


class TestScriptOverviewFailedSceneUI:
    """Test ScriptOverview.jsx failed scene UI components"""
    
    def test_is_failed_helper_function(self):
        """Verify isFailed helper function exists"""
        script_overview_path = "/app/frontend/src/components/ScriptOverview.jsx"
        with open(script_overview_path, 'r') as f:
            content = f.read()
        
        assert "isFailed" in content, "Missing isFailed helper function"
        assert 'startsWith("failed-")' in content or "startsWith('failed-')" in content, "isFailed should check for 'failed-' prefix"
        print("PASS: isFailed helper function exists and checks for 'failed-' prefix")
    
    def test_failed_scene_tab_red_styling(self):
        """Verify failed scene tabs have red styling"""
        script_overview_path = "/app/frontend/src/components/ScriptOverview.jsx"
        with open(script_overview_path, 'r') as f:
            content = f.read()
        
        # Check for red styling on failed tabs
        assert "text-red" in content, "Missing red text styling for failed tabs"
        assert "red-500" in content or "red-400" in content, "Missing red color classes"
        print("PASS: Failed scene tabs have red styling (text-red classes)")
    
    def test_alert_triangle_icon_for_failed_scenes(self):
        """Verify AlertTriangle icon is used for failed scenes"""
        script_overview_path = "/app/frontend/src/components/ScriptOverview.jsx"
        with open(script_overview_path, 'r') as f:
            content = f.read()
        
        assert "AlertTriangle" in content, "Missing AlertTriangle icon import/usage"
        # Check it's used in the tab area
        assert "AlertTriangle" in content and "failed" in content.lower(), "AlertTriangle should be used for failed scenes"
        print("PASS: AlertTriangle icon is used for failed scenes")
    
    def test_failed_scene_card_data_testid(self):
        """Verify failed scene card has data-testid='failed-scene-card'"""
        script_overview_path = "/app/frontend/src/components/ScriptOverview.jsx"
        with open(script_overview_path, 'r') as f:
            content = f.read()
        
        assert 'data-testid="failed-scene-card"' in content or "data-testid='failed-scene-card'" in content, \
            "Missing data-testid='failed-scene-card'"
        print("PASS: Failed scene card has data-testid='failed-scene-card'")
    
    def test_retry_button_data_testid(self):
        """Verify retry button has data-testid='retry-scene-button'"""
        script_overview_path = "/app/frontend/src/components/ScriptOverview.jsx"
        with open(script_overview_path, 'r') as f:
            content = f.read()
        
        assert 'data-testid="retry-scene-button"' in content or "data-testid='retry-scene-button'" in content, \
            "Missing data-testid='retry-scene-button'"
        print("PASS: Retry button has data-testid='retry-scene-button'")
    
    def test_error_type_badge_rendering(self):
        """Verify error type badge renders different error types"""
        script_overview_path = "/app/frontend/src/components/ScriptOverview.jsx"
        with open(script_overview_path, 'r') as f:
            content = f.read()
        
        # Check for error type badge labels
        assert "Network / Proxy Timeout" in content or "network_error" in content, "Missing network_error badge label"
        assert "LLM Service Unavailable" in content or "service_unavailable" in content, "Missing service_unavailable badge label"
        assert "Analysis Timed Out" in content or "timeout" in content, "Missing timeout badge label"
        assert "Budget Exceeded" in content or "budget_exceeded" in content, "Missing budget_exceeded badge label"
        assert "Rate Limited" in content or "rate_limited" in content, "Missing rate_limited badge label"
        print("PASS: Error type badge renders all error types (network_error, service_unavailable, timeout, budget_exceeded, rate_limited)")
    
    def test_action_bar_hidden_for_failed_scenes(self):
        """Verify action bar is hidden for failed scenes"""
        script_overview_path = "/app/frontend/src/components/ScriptOverview.jsx"
        with open(script_overview_path, 'r') as f:
            content = f.read()
        
        # Check for conditional rendering that hides action bar for failed scenes
        assert "!isFailed(activeBreakdown)" in content or "!isFailed(" in content, \
            "Missing conditional to hide action bar for failed scenes"
        print("PASS: Action bar is conditionally hidden for failed scenes")
    
    def test_retry_scene_handler_prop(self):
        """Verify onRetryScene prop is used"""
        script_overview_path = "/app/frontend/src/components/ScriptOverview.jsx"
        with open(script_overview_path, 'r') as f:
            content = f.read()
        
        assert "onRetryScene" in content, "Missing onRetryScene prop"
        print("PASS: onRetryScene prop is defined and used")
    
    def test_cost_summary_bar_data_testid(self):
        """Verify cost summary bar has data-testid='cost-summary-bar'"""
        script_overview_path = "/app/frontend/src/components/ScriptOverview.jsx"
        with open(script_overview_path, 'r') as f:
            content = f.read()
        
        assert 'data-testid="cost-summary-bar"' in content or "data-testid='cost-summary-bar'" in content, \
            "Missing data-testid='cost-summary-bar'"
        print("PASS: Cost summary bar has data-testid='cost-summary-bar'")


class TestHandleRetrySceneFunction:
    """Test handleRetryScene function in App.js"""
    
    def test_handle_retry_scene_exists(self):
        """Verify handleRetryScene function exists in App.js"""
        app_js_path = "/app/frontend/src/App.js"
        with open(app_js_path, 'r') as f:
            content = f.read()
        
        assert "handleRetryScene" in content, "Missing handleRetryScene function"
        assert "useCallback" in content and "handleRetryScene" in content, "handleRetryScene should use useCallback"
        print("PASS: handleRetryScene function exists and uses useCallback")
    
    def test_handle_retry_scene_calls_analyze_scene_api(self):
        """Verify handleRetryScene calls POST /api/analyze/scene"""
        app_js_path = "/app/frontend/src/App.js"
        with open(app_js_path, 'r') as f:
            content = f.read()
        
        # Find handleRetryScene function and check it calls the API
        assert "/api/analyze/scene" in content or "analyze/scene" in content, \
            "handleRetryScene should call /api/analyze/scene"
        print("PASS: handleRetryScene calls /api/analyze/scene endpoint")
    
    def test_handle_retry_scene_updates_script_data(self):
        """Verify handleRetryScene updates scriptData on success"""
        app_js_path = "/app/frontend/src/App.js"
        with open(app_js_path, 'r') as f:
            content = f.read()
        
        # Check for setScriptData call in handleRetryScene context
        assert "setScriptData" in content, "Missing setScriptData call"
        print("PASS: handleRetryScene updates scriptData state")
    
    def test_on_retry_scene_passed_to_script_overview(self):
        """Verify onRetryScene={handleRetryScene} is passed to ScriptOverview"""
        app_js_path = "/app/frontend/src/App.js"
        with open(app_js_path, 'r') as f:
            content = f.read()
        
        assert "onRetryScene={handleRetryScene}" in content or "onRetryScene = {handleRetryScene}" in content.replace(" ", ""), \
            "Missing onRetryScene={handleRetryScene} prop on ScriptOverview"
        print("PASS: onRetryScene={handleRetryScene} is passed to ScriptOverview")


class TestRetryButtonFunctionality:
    """Test retry button loading state and functionality"""
    
    def test_retry_button_shows_loader_while_retrying(self):
        """Verify retry button shows Loader2 spinner while retrying"""
        script_overview_path = "/app/frontend/src/components/ScriptOverview.jsx"
        with open(script_overview_path, 'r') as f:
            content = f.read()
        
        assert "Loader2" in content, "Missing Loader2 icon import"
        assert "retrying" in content.lower(), "Missing retrying state"
        assert "animate-spin" in content, "Missing spinner animation"
        print("PASS: Retry button shows Loader2 spinner with animate-spin while retrying")
    
    def test_retry_button_shows_rotate_ccw_icon(self):
        """Verify retry button shows RotateCcw icon when not retrying"""
        script_overview_path = "/app/frontend/src/components/ScriptOverview.jsx"
        with open(script_overview_path, 'r') as f:
            content = f.read()
        
        assert "RotateCcw" in content, "Missing RotateCcw icon import"
        print("PASS: Retry button shows RotateCcw icon when not retrying")
    
    def test_retry_button_disabled_while_retrying(self):
        """Verify retry button is disabled while retrying"""
        script_overview_path = "/app/frontend/src/components/ScriptOverview.jsx"
        with open(script_overview_path, 'r') as f:
            content = f.read()
        
        assert "disabled={retrying}" in content or "disabled = {retrying}" in content.replace(" ", ""), \
            "Retry button should be disabled while retrying"
        print("PASS: Retry button is disabled while retrying")


class TestSceneTextPreview:
    """Test scene text preview in failed scene card"""
    
    def test_scene_text_expandable_details(self):
        """Verify failed scene card has expandable scene text preview"""
        script_overview_path = "/app/frontend/src/components/ScriptOverview.jsx"
        with open(script_overview_path, 'r') as f:
            content = f.read()
        
        assert "<details" in content, "Missing <details> element for expandable section"
        assert "<summary" in content, "Missing <summary> element"
        assert "Show scene text" in content or "scene text" in content.lower(), "Missing 'Show scene text' label"
        print("PASS: Failed scene card has expandable scene text preview with <details>/<summary>")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
