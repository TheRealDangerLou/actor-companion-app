"""
Test Project CRUD endpoints for Actor's Companion Phase 1 Feature #1
- POST /api/projects — create a project
- GET /api/projects — list all projects sorted by updated_at DESC
- GET /api/projects/{id} — get single project with documents array
- PUT /api/projects/{id} — update project fields
- DELETE /api/projects/{id} — delete project and associated documents
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestProjectCRUD:
    """Project CRUD endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data prefix for cleanup"""
        self.test_prefix = "TEST_PROJECT_"
        self.created_project_ids = []
        yield
        # Cleanup: delete all test-created projects
        for pid in self.created_project_ids:
            try:
                requests.delete(f"{BASE_URL}/api/projects/{pid}")
            except:
                pass
    
    def test_create_audition_project(self):
        """POST /api/projects - create audition project with all fields"""
        payload = {
            "title": f"{self.test_prefix}Netflix Drama Callback",
            "role_name": "Felix",
            "mode": "audition",
            "audition_date": "2026-02-15",
            "audition_time": "14:30",
            "audition_format": "self-tape"
        }
        response = requests.post(f"{BASE_URL}/api/projects", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify all fields returned
        assert "id" in data, "Response should contain id"
        assert data["title"] == payload["title"], f"Title mismatch: {data['title']}"
        assert data["role_name"] == "Felix", f"Role name mismatch: {data['role_name']}"
        assert data["mode"] == "audition", f"Mode mismatch: {data['mode']}"
        assert data["audition_date"] == "2026-02-15", f"Date mismatch: {data['audition_date']}"
        assert data["audition_time"] == "14:30", f"Time mismatch: {data['audition_time']}"
        assert data["audition_format"] == "self-tape", f"Format mismatch: {data['audition_format']}"
        assert "created_at" in data, "Should have created_at"
        assert "updated_at" in data, "Should have updated_at"
        assert data["document_ids"] == [], "Should have empty document_ids"
        
        self.created_project_ids.append(data["id"])
        print(f"✓ Created audition project: {data['id']}")
    
    def test_create_booked_project(self):
        """POST /api/projects - create booked role project (no date/time/format)"""
        payload = {
            "title": f"{self.test_prefix}HBO Series Lead",
            "role_name": "Sarah",
            "mode": "booked"
        }
        response = requests.post(f"{BASE_URL}/api/projects", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["mode"] == "booked", f"Mode should be booked: {data['mode']}"
        assert data["audition_date"] is None, "Booked project should have null audition_date"
        assert data["audition_time"] is None, "Booked project should have null audition_time"
        assert data["audition_format"] is None, "Booked project should have null audition_format"
        
        self.created_project_ids.append(data["id"])
        print(f"✓ Created booked project: {data['id']}")
    
    def test_create_project_minimal(self):
        """POST /api/projects - create project with only required fields"""
        payload = {
            "title": f"{self.test_prefix}Minimal Project"
        }
        response = requests.post(f"{BASE_URL}/api/projects", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["title"] == payload["title"]
        assert data["mode"] == "audition", "Default mode should be audition"
        assert data["role_name"] == "", "Default role_name should be empty string"
        
        self.created_project_ids.append(data["id"])
        print(f"✓ Created minimal project: {data['id']}")
    
    def test_list_projects(self):
        """GET /api/projects - list all projects sorted by updated_at DESC"""
        # Create two projects with slight delay to ensure different updated_at
        payload1 = {"title": f"{self.test_prefix}First Project", "mode": "audition"}
        resp1 = requests.post(f"{BASE_URL}/api/projects", json=payload1)
        assert resp1.status_code == 200
        project1 = resp1.json()
        self.created_project_ids.append(project1["id"])
        
        time.sleep(0.1)  # Small delay to ensure different timestamps
        
        payload2 = {"title": f"{self.test_prefix}Second Project", "mode": "booked"}
        resp2 = requests.post(f"{BASE_URL}/api/projects", json=payload2)
        assert resp2.status_code == 200
        project2 = resp2.json()
        self.created_project_ids.append(project2["id"])
        
        # List projects
        response = requests.get(f"{BASE_URL}/api/projects")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        projects = response.json()
        
        assert isinstance(projects, list), "Response should be a list"
        assert len(projects) >= 2, f"Should have at least 2 projects, got {len(projects)}"
        
        # Find our test projects
        test_projects = [p for p in projects if p["title"].startswith(self.test_prefix)]
        assert len(test_projects) >= 2, f"Should find at least 2 test projects"
        
        # Verify document_count is included
        for p in test_projects:
            assert "document_count" in p, "Each project should have document_count"
            assert isinstance(p["document_count"], int), "document_count should be int"
        
        # Verify sorted by updated_at DESC (most recent first)
        # Second project should appear before first in the list
        project2_idx = next((i for i, p in enumerate(projects) if p["id"] == project2["id"]), -1)
        project1_idx = next((i for i, p in enumerate(projects) if p["id"] == project1["id"]), -1)
        assert project2_idx < project1_idx, "Projects should be sorted by updated_at DESC"
        
        print(f"✓ Listed {len(projects)} projects, sorted correctly")
    
    def test_get_single_project(self):
        """GET /api/projects/{id} - get single project with documents array"""
        # Create a project
        payload = {"title": f"{self.test_prefix}Single Project Test", "role_name": "TestRole"}
        create_resp = requests.post(f"{BASE_URL}/api/projects", json=payload)
        assert create_resp.status_code == 200
        created = create_resp.json()
        self.created_project_ids.append(created["id"])
        
        # Get the project
        response = requests.get(f"{BASE_URL}/api/projects/{created['id']}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert data["id"] == created["id"], "ID should match"
        assert data["title"] == payload["title"], "Title should match"
        assert data["role_name"] == "TestRole", "Role name should match"
        assert "documents" in data, "Should include documents array"
        assert isinstance(data["documents"], list), "documents should be a list"
        
        print(f"✓ Got single project with documents array")
    
    def test_get_project_not_found(self):
        """GET /api/projects/{id} - returns 404 for non-existent project"""
        response = requests.get(f"{BASE_URL}/api/projects/non-existent-id-12345")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Returns 404 for non-existent project")
    
    def test_update_project(self):
        """PUT /api/projects/{id} - update project fields"""
        # Create a project
        payload = {"title": f"{self.test_prefix}Update Test", "role_name": "OldRole", "mode": "audition"}
        create_resp = requests.post(f"{BASE_URL}/api/projects", json=payload)
        assert create_resp.status_code == 200
        created = create_resp.json()
        self.created_project_ids.append(created["id"])
        original_updated_at = created["updated_at"]
        
        time.sleep(0.1)  # Ensure different timestamp
        
        # Update the project
        update_payload = {
            "title": f"{self.test_prefix}Updated Title",
            "role_name": "NewRole",
            "selected_character": "Felix"
        }
        response = requests.put(f"{BASE_URL}/api/projects/{created['id']}", json=update_payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["title"] == update_payload["title"], "Title should be updated"
        assert data["role_name"] == "NewRole", "Role name should be updated"
        assert data["selected_character"] == "Felix", "Selected character should be updated"
        assert data["updated_at"] != original_updated_at, "updated_at should change"
        
        # Verify persistence with GET
        get_resp = requests.get(f"{BASE_URL}/api/projects/{created['id']}")
        assert get_resp.status_code == 200
        fetched = get_resp.json()
        assert fetched["title"] == update_payload["title"], "Updated title should persist"
        
        print(f"✓ Updated project and verified persistence")
    
    def test_update_project_not_found(self):
        """PUT /api/projects/{id} - returns 404 for non-existent project"""
        response = requests.put(
            f"{BASE_URL}/api/projects/non-existent-id-12345",
            json={"title": "New Title"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Returns 404 for updating non-existent project")
    
    def test_update_project_no_fields(self):
        """PUT /api/projects/{id} - returns 400 when no fields to update"""
        # Create a project
        payload = {"title": f"{self.test_prefix}No Update Test"}
        create_resp = requests.post(f"{BASE_URL}/api/projects", json=payload)
        assert create_resp.status_code == 200
        created = create_resp.json()
        self.created_project_ids.append(created["id"])
        
        # Try to update with empty payload
        response = requests.put(f"{BASE_URL}/api/projects/{created['id']}", json={})
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print(f"✓ Returns 400 when no fields to update")
    
    def test_delete_project(self):
        """DELETE /api/projects/{id} - delete project"""
        # Create a project
        payload = {"title": f"{self.test_prefix}Delete Test"}
        create_resp = requests.post(f"{BASE_URL}/api/projects", json=payload)
        assert create_resp.status_code == 200
        created = create_resp.json()
        project_id = created["id"]
        
        # Delete the project
        response = requests.delete(f"{BASE_URL}/api/projects/{project_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["status"] == "deleted", "Should return deleted status"
        assert data["project_id"] == project_id, "Should return project_id"
        
        # Verify deletion with GET
        get_resp = requests.get(f"{BASE_URL}/api/projects/{project_id}")
        assert get_resp.status_code == 404, "Deleted project should return 404"
        
        print(f"✓ Deleted project and verified removal")
    
    def test_delete_project_not_found(self):
        """DELETE /api/projects/{id} - returns 404 for non-existent project"""
        response = requests.delete(f"{BASE_URL}/api/projects/non-existent-id-12345")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Returns 404 for deleting non-existent project")
    
    def test_create_and_verify_persistence(self):
        """Full CRUD flow: Create → GET → Update → GET → Delete → GET"""
        # CREATE
        payload = {
            "title": f"{self.test_prefix}Full CRUD Test",
            "role_name": "TestActor",
            "mode": "audition",
            "audition_date": "2026-03-01",
            "audition_time": "10:00",
            "audition_format": "in-person"
        }
        create_resp = requests.post(f"{BASE_URL}/api/projects", json=payload)
        assert create_resp.status_code == 200
        created = create_resp.json()
        project_id = created["id"]
        
        # GET to verify creation
        get_resp = requests.get(f"{BASE_URL}/api/projects/{project_id}")
        assert get_resp.status_code == 200
        fetched = get_resp.json()
        assert fetched["title"] == payload["title"]
        assert fetched["audition_format"] == "in-person"
        
        # UPDATE
        update_resp = requests.put(
            f"{BASE_URL}/api/projects/{project_id}",
            json={"audition_format": "self-tape", "role_name": "UpdatedActor"}
        )
        assert update_resp.status_code == 200
        
        # GET to verify update
        get_resp2 = requests.get(f"{BASE_URL}/api/projects/{project_id}")
        assert get_resp2.status_code == 200
        updated = get_resp2.json()
        assert updated["audition_format"] == "self-tape"
        assert updated["role_name"] == "UpdatedActor"
        
        # DELETE
        delete_resp = requests.delete(f"{BASE_URL}/api/projects/{project_id}")
        assert delete_resp.status_code == 200
        
        # GET to verify deletion
        get_resp3 = requests.get(f"{BASE_URL}/api/projects/{project_id}")
        assert get_resp3.status_code == 404
        
        print(f"✓ Full CRUD flow completed successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
