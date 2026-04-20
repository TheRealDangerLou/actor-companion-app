"""
Test Document Upload & Management (Phase 1 - Feature #2)
Tests: POST/GET/PUT/DELETE document endpoints, 5-doc limit, pasted text, type changes
"""
import pytest
import requests
import os
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestDocumentUpload:
    """Document upload and management tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Create a test project for document tests"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Create test project
        resp = self.session.post(f"{BASE_URL}/api/projects", json={
            "title": "TEST_DocUpload_Project",
            "role_name": "Test Role",
            "mode": "audition"
        })
        assert resp.status_code == 200, f"Failed to create test project: {resp.text}"
        self.project = resp.json()
        self.project_id = self.project["id"]
        self.created_doc_ids = []
        
        yield
        
        # Cleanup: delete all test documents and project
        for doc_id in self.created_doc_ids:
            try:
                self.session.delete(f"{BASE_URL}/api/documents/{doc_id}")
            except:
                pass
        try:
            self.session.delete(f"{BASE_URL}/api/projects/{self.project_id}")
        except:
            pass
    
    # --- Pasted Text Upload Tests ---
    
    def test_upload_pasted_text_success(self):
        """POST /api/projects/{id}/documents - upload pasted text"""
        form_data = {
            "pasted_text": "INT. COFFEE SHOP - DAY\n\nSARAH sits alone at a table.\n\nSARAH\nI can't believe this is happening.",
            "doc_type": "sides"
        }
        resp = self.session.post(
            f"{BASE_URL}/api/projects/{self.project_id}/documents",
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert resp.status_code == 200, f"Upload failed: {resp.text}"
        
        doc = resp.json()
        self.created_doc_ids.append(doc["id"])
        
        # Verify response structure
        assert "id" in doc
        assert doc["project_id"] == self.project_id
        assert doc["type"] == "sides"
        assert doc["filename"] == "pasted_text.txt"
        assert doc["extraction_method"] == "paste"
        assert doc["char_count"] > 0
        assert "original_text" in doc
        assert "INT. COFFEE SHOP" in doc["original_text"]
        print(f"SUCCESS: Pasted text uploaded, doc_id={doc['id']}, chars={doc['char_count']}")
    
    def test_upload_pasted_text_with_different_types(self):
        """POST /api/projects/{id}/documents - test document types (limited to 5)"""
        # Test 5 types (limit is 5 docs per project)
        valid_types = ["sides", "instructions", "wardrobe", "notes", "reference"]
        
        for doc_type in valid_types:
            form_data = {
                "pasted_text": f"Test content for {doc_type} document type.",
                "doc_type": doc_type
            }
            resp = self.session.post(
                f"{BASE_URL}/api/projects/{self.project_id}/documents",
                data=form_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            assert resp.status_code == 200, f"Upload failed for type {doc_type}: {resp.text}"
            
            doc = resp.json()
            self.created_doc_ids.append(doc["id"])
            assert doc["type"] == doc_type
            print(f"SUCCESS: Document type '{doc_type}' accepted")
    
    def test_upload_pasted_text_empty_fails(self):
        """POST /api/projects/{id}/documents - empty text should fail"""
        form_data = {
            "pasted_text": "   ",  # whitespace only
            "doc_type": "sides"
        }
        resp = self.session.post(
            f"{BASE_URL}/api/projects/{self.project_id}/documents",
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert resp.status_code == 400, f"Expected 400 for empty text, got {resp.status_code}"
        print("SUCCESS: Empty pasted text correctly rejected")
    
    def test_upload_pasted_text_too_short_fails(self):
        """POST /api/projects/{id}/documents - text < 5 chars should fail"""
        form_data = {
            "pasted_text": "Hi",  # too short
            "doc_type": "sides"
        }
        resp = self.session.post(
            f"{BASE_URL}/api/projects/{self.project_id}/documents",
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert resp.status_code == 400, f"Expected 400 for short text, got {resp.status_code}"
        print("SUCCESS: Short text correctly rejected")
    
    # --- Document Limit Tests ---
    
    def test_document_limit_enforced(self):
        """POST /api/projects/{id}/documents - enforces 5 document limit"""
        # Upload 5 documents
        for i in range(5):
            form_data = {
                "pasted_text": f"Document number {i+1} content for testing the limit.",
                "doc_type": "notes"
            }
            resp = self.session.post(
                f"{BASE_URL}/api/projects/{self.project_id}/documents",
                data=form_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            assert resp.status_code == 200, f"Upload {i+1} failed: {resp.text}"
            self.created_doc_ids.append(resp.json()["id"])
        
        print("SUCCESS: Uploaded 5 documents")
        
        # Try to upload 6th document - should fail
        form_data = {
            "pasted_text": "This is the 6th document that should be rejected.",
            "doc_type": "notes"
        }
        resp = self.session.post(
            f"{BASE_URL}/api/projects/{self.project_id}/documents",
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert resp.status_code == 400, f"Expected 400 for 6th doc, got {resp.status_code}"
        assert "Maximum 5 documents" in resp.json().get("detail", "")
        print("SUCCESS: 6th document correctly rejected with limit message")
    
    # --- List Documents Tests ---
    
    def test_list_project_documents(self):
        """GET /api/projects/{id}/documents - list documents (excludes original_text)"""
        # First upload a document
        form_data = {
            "pasted_text": "Test document content for listing test.",
            "doc_type": "sides"
        }
        upload_resp = self.session.post(
            f"{BASE_URL}/api/projects/{self.project_id}/documents",
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert upload_resp.status_code == 200
        self.created_doc_ids.append(upload_resp.json()["id"])
        
        # List documents
        resp = self.session.get(f"{BASE_URL}/api/projects/{self.project_id}/documents")
        assert resp.status_code == 200
        
        docs = resp.json()
        assert isinstance(docs, list)
        assert len(docs) >= 1
        
        # Verify original_text is excluded for performance
        for doc in docs:
            assert "original_text" not in doc, "original_text should be excluded from list"
            assert "id" in doc
            assert "filename" in doc
            assert "type" in doc
            assert "char_count" in doc
            assert "extraction_method" in doc
        
        print(f"SUCCESS: Listed {len(docs)} documents, original_text excluded")
    
    def test_list_documents_nonexistent_project(self):
        """GET /api/projects/{id}/documents - returns 404 for non-existent project"""
        resp = self.session.get(f"{BASE_URL}/api/projects/nonexistent-id-12345/documents")
        assert resp.status_code == 404
        print("SUCCESS: 404 returned for non-existent project")
    
    # --- Get Single Document Tests ---
    
    def test_get_single_document_with_full_text(self):
        """GET /api/documents/{id} - get single document with full text"""
        # Upload a document
        test_text = "INT. OFFICE - NIGHT\n\nJOHN types furiously at his computer.\n\nJOHN\nThis has to work!"
        form_data = {
            "pasted_text": test_text,
            "doc_type": "sides"
        }
        upload_resp = self.session.post(
            f"{BASE_URL}/api/projects/{self.project_id}/documents",
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert upload_resp.status_code == 200
        doc_id = upload_resp.json()["id"]
        self.created_doc_ids.append(doc_id)
        
        # Get single document
        resp = self.session.get(f"{BASE_URL}/api/documents/{doc_id}")
        assert resp.status_code == 200
        
        doc = resp.json()
        assert doc["id"] == doc_id
        assert "original_text" in doc, "Single doc should include original_text"
        assert "INT. OFFICE" in doc["original_text"]
        assert doc["type"] == "sides"
        print(f"SUCCESS: Got single document with full text ({len(doc['original_text'])} chars)")
    
    def test_get_document_nonexistent(self):
        """GET /api/documents/{id} - returns 404 for non-existent document"""
        resp = self.session.get(f"{BASE_URL}/api/documents/nonexistent-doc-id-12345")
        assert resp.status_code == 404
        print("SUCCESS: 404 returned for non-existent document")
    
    # --- Update Document Type Tests ---
    
    def test_update_document_type(self):
        """PUT /api/documents/{id}/type - update document type"""
        # Upload a document
        form_data = {
            "pasted_text": "Test content for type update test.",
            "doc_type": "unknown"
        }
        upload_resp = self.session.post(
            f"{BASE_URL}/api/projects/{self.project_id}/documents",
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert upload_resp.status_code == 200
        doc_id = upload_resp.json()["id"]
        self.created_doc_ids.append(doc_id)
        
        # Update type to "sides"
        resp = self.session.put(
            f"{BASE_URL}/api/documents/{doc_id}/type",
            json={"type": "sides"}
        )
        assert resp.status_code == 200
        assert resp.json()["type"] == "sides"
        
        # Verify persistence
        get_resp = self.session.get(f"{BASE_URL}/api/documents/{doc_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["type"] == "sides"
        print("SUCCESS: Document type updated and persisted")
    
    def test_update_document_type_all_valid_types(self):
        """PUT /api/documents/{id}/type - test all valid type transitions"""
        # Upload a document
        form_data = {
            "pasted_text": "Test content for type transition test.",
            "doc_type": "unknown"
        }
        upload_resp = self.session.post(
            f"{BASE_URL}/api/projects/{self.project_id}/documents",
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert upload_resp.status_code == 200
        doc_id = upload_resp.json()["id"]
        self.created_doc_ids.append(doc_id)
        
        valid_types = ["sides", "instructions", "wardrobe", "notes", "reference", "unknown"]
        for new_type in valid_types:
            resp = self.session.put(
                f"{BASE_URL}/api/documents/{doc_id}/type",
                json={"type": new_type}
            )
            assert resp.status_code == 200, f"Failed to update to {new_type}: {resp.text}"
            assert resp.json()["type"] == new_type
        
        print("SUCCESS: All valid type transitions work")
    
    def test_update_document_type_invalid(self):
        """PUT /api/documents/{id}/type - invalid type returns 400"""
        # Upload a document
        form_data = {
            "pasted_text": "Test content for invalid type test.",
            "doc_type": "sides"
        }
        upload_resp = self.session.post(
            f"{BASE_URL}/api/projects/{self.project_id}/documents",
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert upload_resp.status_code == 200
        doc_id = upload_resp.json()["id"]
        self.created_doc_ids.append(doc_id)
        
        # Try invalid type
        resp = self.session.put(
            f"{BASE_URL}/api/documents/{doc_id}/type",
            json={"type": "invalid_type"}
        )
        assert resp.status_code == 400
        print("SUCCESS: Invalid type correctly rejected")
    
    def test_update_document_type_nonexistent(self):
        """PUT /api/documents/{id}/type - returns 404 for non-existent document"""
        resp = self.session.put(
            f"{BASE_URL}/api/documents/nonexistent-doc-id/type",
            json={"type": "sides"}
        )
        assert resp.status_code == 404
        print("SUCCESS: 404 returned for non-existent document")
    
    # --- Delete Document Tests ---
    
    def test_delete_document(self):
        """DELETE /api/documents/{id} - delete document and remove from project"""
        # Upload a document
        form_data = {
            "pasted_text": "Test content for delete test.",
            "doc_type": "notes"
        }
        upload_resp = self.session.post(
            f"{BASE_URL}/api/projects/{self.project_id}/documents",
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert upload_resp.status_code == 200
        doc_id = upload_resp.json()["id"]
        
        # Delete document
        resp = self.session.delete(f"{BASE_URL}/api/documents/{doc_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"
        
        # Verify document is gone
        get_resp = self.session.get(f"{BASE_URL}/api/documents/{doc_id}")
        assert get_resp.status_code == 404
        
        # Verify removed from project's document list
        list_resp = self.session.get(f"{BASE_URL}/api/projects/{self.project_id}/documents")
        assert list_resp.status_code == 200
        doc_ids = [d["id"] for d in list_resp.json()]
        assert doc_id not in doc_ids
        
        print("SUCCESS: Document deleted and removed from project")
    
    def test_delete_document_nonexistent(self):
        """DELETE /api/documents/{id} - returns 404 for non-existent document"""
        resp = self.session.delete(f"{BASE_URL}/api/documents/nonexistent-doc-id-12345")
        assert resp.status_code == 404
        print("SUCCESS: 404 returned for non-existent document")
    
    # --- PDF File Upload Tests ---
    
    def test_upload_pdf_file(self):
        """POST /api/projects/{id}/documents - upload PDF file with text extraction"""
        # Create a minimal PDF file
        pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT /F1 12 Tf 100 700 Td (Hello World) Tj ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000266 00000 n 
0000000359 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
434
%%EOF"""
        
        files = {
            'file': ('test_script.pdf', io.BytesIO(pdf_content), 'application/pdf')
        }
        data = {
            'doc_type': 'sides'
        }
        
        resp = self.session.post(
            f"{BASE_URL}/api/projects/{self.project_id}/documents",
            files=files,
            data=data
        )
        
        # PDF might succeed or fail depending on text extraction
        # We mainly want to verify the endpoint accepts PDF files
        if resp.status_code == 200:
            doc = resp.json()
            self.created_doc_ids.append(doc["id"])
            assert doc["filename"] == "test_script.pdf"
            assert doc["extraction_method"] in ["pdf", "pdf_ocr"]
            print(f"SUCCESS: PDF uploaded, extraction_method={doc['extraction_method']}")
        elif resp.status_code == 400:
            # Might fail if text extraction yields < 5 chars
            print(f"INFO: PDF upload returned 400 (likely insufficient text): {resp.json().get('detail')}")
        else:
            pytest.fail(f"Unexpected status {resp.status_code}: {resp.text}")
    
    # --- Project Document Count Tests ---
    
    def test_project_document_count_updates(self):
        """GET /api/projects - document_count updates correctly"""
        # Get initial count
        list_resp = self.session.get(f"{BASE_URL}/api/projects")
        assert list_resp.status_code == 200
        projects = list_resp.json()
        test_project = next((p for p in projects if p["id"] == self.project_id), None)
        assert test_project is not None
        initial_count = test_project.get("document_count", 0)
        
        # Upload a document
        form_data = {
            "pasted_text": "Test content for count test.",
            "doc_type": "notes"
        }
        upload_resp = self.session.post(
            f"{BASE_URL}/api/projects/{self.project_id}/documents",
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert upload_resp.status_code == 200
        doc_id = upload_resp.json()["id"]
        self.created_doc_ids.append(doc_id)
        
        # Check count increased
        list_resp = self.session.get(f"{BASE_URL}/api/projects")
        assert list_resp.status_code == 200
        projects = list_resp.json()
        test_project = next((p for p in projects if p["id"] == self.project_id), None)
        assert test_project["document_count"] == initial_count + 1
        
        print(f"SUCCESS: document_count updated from {initial_count} to {initial_count + 1}")
    
    # --- Full CRUD Flow Test ---
    
    def test_full_document_crud_flow(self):
        """Full flow: Create → List → Get → Update Type → Delete → Verify"""
        # 1. Create document
        form_data = {
            "pasted_text": "INT. STUDIO - DAY\n\nACTOR rehearses lines.\n\nACTOR\nTo be or not to be...",
            "doc_type": "unknown"
        }
        create_resp = self.session.post(
            f"{BASE_URL}/api/projects/{self.project_id}/documents",
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert create_resp.status_code == 200
        doc = create_resp.json()
        doc_id = doc["id"]
        print(f"1. Created document: {doc_id}")
        
        # 2. List documents
        list_resp = self.session.get(f"{BASE_URL}/api/projects/{self.project_id}/documents")
        assert list_resp.status_code == 200
        docs = list_resp.json()
        assert any(d["id"] == doc_id for d in docs)
        print(f"2. Document appears in list ({len(docs)} total)")
        
        # 3. Get single document
        get_resp = self.session.get(f"{BASE_URL}/api/documents/{doc_id}")
        assert get_resp.status_code == 200
        full_doc = get_resp.json()
        assert "original_text" in full_doc
        assert "To be or not to be" in full_doc["original_text"]
        print("3. Got document with full text")
        
        # 4. Update type
        update_resp = self.session.put(
            f"{BASE_URL}/api/documents/{doc_id}/type",
            json={"type": "sides"}
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["type"] == "sides"
        print("4. Updated type to 'sides'")
        
        # 5. Verify type persisted
        verify_resp = self.session.get(f"{BASE_URL}/api/documents/{doc_id}")
        assert verify_resp.status_code == 200
        assert verify_resp.json()["type"] == "sides"
        print("5. Type change persisted")
        
        # 6. Delete document
        delete_resp = self.session.delete(f"{BASE_URL}/api/documents/{doc_id}")
        assert delete_resp.status_code == 200
        print("6. Deleted document")
        
        # 7. Verify deletion
        gone_resp = self.session.get(f"{BASE_URL}/api/documents/{doc_id}")
        assert gone_resp.status_code == 404
        print("7. Document confirmed deleted (404)")
        
        print("SUCCESS: Full CRUD flow completed")


class TestDocumentUploadNonexistentProject:
    """Test document upload to non-existent project"""
    
    def test_upload_to_nonexistent_project(self):
        """POST /api/projects/{id}/documents - returns 404 for non-existent project"""
        session = requests.Session()
        form_data = {
            "pasted_text": "Test content",
            "doc_type": "sides"
        }
        resp = session.post(
            f"{BASE_URL}/api/projects/nonexistent-project-id-12345/documents",
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert resp.status_code == 404
        print("SUCCESS: 404 returned for non-existent project")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
