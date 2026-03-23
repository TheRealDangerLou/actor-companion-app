"""
Test Deterministic Line Extraction (Zero GPT) - Iteration 22
Tests the /api/parse-lines endpoint and deterministic line extraction logic.
Features tested:
1. POST /api/parse-lines extracts character lines without GPT
2. cue_recall format: {cue: previous speaker's line, your_line: character's line}
3. Edge cases: (V.O.), (CONT'D), multiple consecutive lines
4. chunked_lines grouping (groups of 3)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestDeterministicLineExtraction:
    """Test the /api/parse-lines endpoint for deterministic line extraction."""

    def test_api_root_accessible(self):
        """Verify API is accessible."""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        print("PASS: API root accessible")

    def test_parse_lines_basic(self):
        """Test basic line extraction with standard screenplay format."""
        script_text = """JOHN
I need to talk to you.

SARAH
Not now.

JOHN
It can't wait."""

        response = requests.post(
            f"{BASE_URL}/api/parse-lines",
            json={"text": script_text, "character_name": "JOHN"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "character_name" in data
        assert "line_count" in data
        assert "memorization" in data
        assert "cue_recall" in data["memorization"]
        assert "chunked_lines" in data["memorization"]
        
        # JOHN has 2 lines in this script
        assert data["line_count"] == 2, f"Expected 2 lines for JOHN, got {data['line_count']}"
        assert data["character_name"] == "JOHN"
        
        cue_recall = data["memorization"]["cue_recall"]
        assert len(cue_recall) == 2
        
        # First line: cue is "(Scene start)" since JOHN speaks first
        assert cue_recall[0]["cue"] == "(Scene start)"
        assert "I need to talk to you" in cue_recall[0]["your_line"]
        
        # Second line: cue is SARAH's line
        assert "SARAH" in cue_recall[1]["cue"]
        assert "Not now" in cue_recall[1]["cue"]
        assert "can't wait" in cue_recall[1]["your_line"]
        
        print(f"PASS: Basic line extraction - {data['line_count']} lines for JOHN")
        print(f"  Cue 1: {cue_recall[0]['cue'][:50]}...")
        print(f"  Line 1: {cue_recall[0]['your_line'][:50]}...")

    def test_parse_lines_with_vo(self):
        """Test line extraction with (V.O.) parenthetical."""
        script_text = """NARRATOR (V.O.)
The city never sleeps.

JOHN
I know what you mean.

NARRATOR (V.O.)
But tonight was different."""

        response = requests.post(
            f"{BASE_URL}/api/parse-lines",
            json={"text": script_text, "character_name": "NARRATOR"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # NARRATOR has 2 lines (both V.O.)
        assert data["line_count"] == 2, f"Expected 2 lines for NARRATOR, got {data['line_count']}"
        
        cue_recall = data["memorization"]["cue_recall"]
        assert len(cue_recall) == 2
        
        # First line: scene start
        assert cue_recall[0]["cue"] == "(Scene start)"
        assert "city never sleeps" in cue_recall[0]["your_line"]
        
        # Second line: cue is JOHN's line
        assert "JOHN" in cue_recall[1]["cue"]
        assert "tonight was different" in cue_recall[1]["your_line"]
        
        print(f"PASS: V.O. handling - {data['line_count']} lines for NARRATOR")

    def test_parse_lines_with_contd(self):
        """Test line extraction with (CONT'D) parenthetical."""
        script_text = """SARAH
Wait, I have something to say.

JOHN
What is it?

SARAH (CONT'D)
I've been thinking about us."""

        response = requests.post(
            f"{BASE_URL}/api/parse-lines",
            json={"text": script_text, "character_name": "SARAH"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # SARAH has 2 lines (one regular, one CONT'D)
        assert data["line_count"] == 2, f"Expected 2 lines for SARAH, got {data['line_count']}"
        
        cue_recall = data["memorization"]["cue_recall"]
        assert len(cue_recall) == 2
        
        print(f"PASS: CONT'D handling - {data['line_count']} lines for SARAH")

    def test_parse_lines_multiple_consecutive(self):
        """Test extraction when character has multiple consecutive lines."""
        script_text = """JOHN
First line.

JOHN
Second line.

JOHN
Third line.

SARAH
Finally, my turn."""

        response = requests.post(
            f"{BASE_URL}/api/parse-lines",
            json={"text": script_text, "character_name": "JOHN"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # JOHN has 3 consecutive lines
        assert data["line_count"] == 3, f"Expected 3 lines for JOHN, got {data['line_count']}"
        
        cue_recall = data["memorization"]["cue_recall"]
        assert len(cue_recall) == 3
        
        # Each JOHN line should have the previous JOHN line as cue (except first)
        assert cue_recall[0]["cue"] == "(Scene start)"
        assert "JOHN" in cue_recall[1]["cue"]  # Previous JOHN line
        assert "JOHN" in cue_recall[2]["cue"]  # Previous JOHN line
        
        print(f"PASS: Multiple consecutive lines - {data['line_count']} lines for JOHN")

    def test_parse_lines_chunked_lines(self):
        """Test that chunked_lines groups lines in chunks of 3."""
        script_text = """SARAH
Line one.

JOHN
Response one.

SARAH
Line two.

JOHN
Response two.

SARAH
Line three.

JOHN
Response three.

SARAH
Line four.

JOHN
Response four.

SARAH
Line five."""

        response = requests.post(
            f"{BASE_URL}/api/parse-lines",
            json={"text": script_text, "character_name": "SARAH"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # SARAH has 5 lines
        assert data["line_count"] == 5, f"Expected 5 lines for SARAH, got {data['line_count']}"
        
        chunked_lines = data["memorization"]["chunked_lines"]
        # 5 lines should be in 2 chunks: [3, 2]
        assert len(chunked_lines) >= 2, f"Expected at least 2 chunks, got {len(chunked_lines)}"
        
        # First chunk should have 3 lines
        assert "Chunk 1" in chunked_lines[0]["chunk_label"]
        assert "3 lines" in chunked_lines[0]["chunk_label"]
        
        print(f"PASS: Chunked lines - {len(chunked_lines)} chunks for 5 lines")

    def test_parse_lines_empty_text(self):
        """Test with empty text."""
        response = requests.post(
            f"{BASE_URL}/api/parse-lines",
            json={"text": "", "character_name": "JOHN"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["line_count"] == 0
        assert data["memorization"]["cue_recall"] == []
        assert data["memorization"]["chunked_lines"] == []
        
        print("PASS: Empty text returns empty result")

    def test_parse_lines_character_not_found(self):
        """Test when character is not in the script."""
        script_text = """JOHN
Hello there.

SARAH
Hi John."""

        response = requests.post(
            f"{BASE_URL}/api/parse-lines",
            json={"text": script_text, "character_name": "MIKE"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["line_count"] == 0
        assert data["memorization"]["cue_recall"] == []
        
        print("PASS: Character not found returns 0 lines")

    def test_parse_lines_case_insensitive(self):
        """Test that character name matching is case-insensitive."""
        script_text = """JOHN
Hello there.

SARAH
Hi John."""

        # Test with lowercase
        response = requests.post(
            f"{BASE_URL}/api/parse-lines",
            json={"text": script_text, "character_name": "john"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["line_count"] == 1, f"Expected 1 line for 'john', got {data['line_count']}"
        
        print("PASS: Case-insensitive character matching")

    def test_parse_lines_with_parentheticals_in_dialogue(self):
        """Test that parentheticals like (beat), (pause) are skipped."""
        script_text = """JOHN
I don't know what to say.
(beat)
Maybe I should just leave.

SARAH
Don't go."""

        response = requests.post(
            f"{BASE_URL}/api/parse-lines",
            json={"text": script_text, "character_name": "JOHN"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # JOHN has 1 dialogue block (parenthetical should be skipped)
        assert data["line_count"] == 1
        
        # The dialogue should combine both lines (before and after beat)
        your_line = data["memorization"]["cue_recall"][0]["your_line"]
        assert "don't know" in your_line.lower()
        assert "leave" in your_line.lower()
        # Parenthetical should NOT be in the line
        assert "(beat)" not in your_line
        
        print("PASS: Parentheticals in dialogue are skipped")

    def test_parse_lines_skips_scene_headings(self):
        """Test that scene headings (INT./EXT.) are not treated as characters."""
        script_text = """INT. COFFEE SHOP - DAY

JOHN
I'll have a coffee.

EXT. STREET - CONTINUOUS

JOHN
That was good."""

        response = requests.post(
            f"{BASE_URL}/api/parse-lines",
            json={"text": script_text, "character_name": "JOHN"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # JOHN has 2 lines
        assert data["line_count"] == 2
        
        # INT. and EXT. should not appear as cues
        for cr in data["memorization"]["cue_recall"]:
            assert "INT." not in cr["cue"]
            assert "EXT." not in cr["cue"]
        
        print("PASS: Scene headings are not treated as characters")


class TestAnalyzeSceneDeterministicOverride:
    """Test that /api/analyze/scene overrides GPT memorization with deterministic extraction."""

    def test_analyze_text_has_deterministic_memorization(self):
        """Test that /api/analyze/text includes deterministic memorization."""
        script_text = """JOHN
I need to talk to you about something important.

SARAH
What is it?

JOHN
It's about the project. We need to make changes."""

        response = requests.post(
            f"{BASE_URL}/api/analyze/text",
            json={"text": script_text, "mode": "quick"}
        )
        
        # This may take time due to GPT call
        assert response.status_code == 200
        data = response.json()
        
        # Check that memorization exists
        assert "memorization" in data
        assert "cue_recall" in data["memorization"]
        
        # If character was detected, memorization should have deterministic lines
        if data.get("character_name") and data["character_name"].upper() in ["JOHN", "SARAH"]:
            cue_recall = data["memorization"]["cue_recall"]
            if cue_recall:
                print(f"PASS: analyze/text has deterministic memorization - {len(cue_recall)} lines")
                # Verify cue_recall structure
                assert "cue" in cue_recall[0]
                assert "your_line" in cue_recall[0]
            else:
                print("INFO: No cue_recall lines (character may not have been detected)")
        else:
            print(f"INFO: Character detected as '{data.get('character_name')}' - skipping line count check")


class TestParseLinesResponseFormat:
    """Test the exact response format of /api/parse-lines."""

    def test_response_structure(self):
        """Verify the exact response structure."""
        script_text = """JOHN
Hello.

SARAH
Hi."""

        response = requests.post(
            f"{BASE_URL}/api/parse-lines",
            json={"text": script_text, "character_name": "JOHN"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Top-level fields
        assert "character_name" in data
        assert "line_count" in data
        assert "memorization" in data
        
        # Memorization fields
        mem = data["memorization"]
        assert "chunked_lines" in mem
        assert "cue_recall" in mem
        
        # cue_recall item structure
        if mem["cue_recall"]:
            cr = mem["cue_recall"][0]
            assert "cue" in cr
            assert "your_line" in cr
        
        # chunked_lines item structure
        if mem["chunked_lines"]:
            cl = mem["chunked_lines"][0]
            assert "chunk_label" in cl
            assert "lines" in cl
        
        print("PASS: Response structure is correct")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
