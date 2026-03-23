"""
Regression tests for extract_character_lines parser.
Tests the exact edge cases that caused failures in production:
- Action text not separated by blank lines
- Names followed by verbs (e.g., "Ivy grabs", "Felix enters")
- Dialogue continuations starting with lowercase
- Parentheticals mid-dialogue
- Dense soap/vertical formatting
All tests run locally against the function — zero GPT, zero credits.
"""
import sys
sys.path.insert(0, '/app/backend')
from server import extract_character_lines


class TestActionTextFiltering:
    """Parser must NOT absorb action/stage directions into dialogue."""

    def test_action_after_dialogue_no_blank_line(self):
        """Action line immediately after dialogue (no blank line separator)."""
        text = """FELIX
I can't believe you said that.
Ivy looks at him, stunned.

IVY
What did you expect?"""
        result = extract_character_lines(text, "FELIX")
        assert result["cue_recall"][0]["your_line"] == "I can't believe you said that."
        # Must NOT include "Ivy looks at him, stunned."
        assert "looks at him" not in result["cue_recall"][0]["your_line"]

    def test_name_plus_verb_is_action(self):
        """'Character + verb' pattern is action, not dialogue."""
        text = """IVY
I'm leaving.
Felix grabs her arm.

FELIX
Wait."""
        result = extract_character_lines(text, "IVY")
        assert len(result["cue_recall"]) == 1
        assert "grabs" not in result["cue_recall"][0]["your_line"]
        assert result["cue_recall"][0]["your_line"] == "I'm leaving."

    def test_name_plus_is_was_action(self):
        """'Name is/was ...' is action, not dialogue."""
        text = """FELIX
Fine. Go then.
Ivy is already halfway out the door.

IVY
Don't follow me."""
        result = extract_character_lines(text, "FELIX")
        assert len(result["cue_recall"]) == 1
        assert "halfway" not in result["cue_recall"][0]["your_line"]

    def test_name_plus_adverb_verb(self):
        """'Name slowly walks...' is action."""
        text = """IVY
I need a moment alone.
Felix slowly begins to crawl toward her.

FELIX
I'm sorry."""
        result = extract_character_lines(text, "IVY")
        assert len(result["cue_recall"]) == 1
        assert "crawl" not in result["cue_recall"][0]["your_line"]

    def test_we_see_they_patterns(self):
        """'We see...', 'They ...' patterns are action."""
        text = """FELIX
Let's do this.
We see the door open slowly.
They move toward the exit.

IVY
After you."""
        result = extract_character_lines(text, "FELIX")
        assert len(result["cue_recall"]) == 1
        assert "door" not in result["cue_recall"][0]["your_line"]


class TestDialogueContinuations:
    """Parser must correctly handle multi-line dialogue and continuations."""

    def test_multiline_dialogue_single_block(self):
        """Multiple lines of dialogue under one character header = one block."""
        text = """FELIX
I don't know what to say.
Maybe I should just leave.
This isn't working.

IVY
Stay."""
        result = extract_character_lines(text, "FELIX")
        assert len(result["cue_recall"]) == 1
        line = result["cue_recall"][0]["your_line"]
        assert "don't know" in line
        assert "leave" in line
        assert "isn't working" in line

    def test_dialogue_starting_with_and_but(self):
        """Lines starting with 'and', 'but' are dialogue continuations, not action."""
        text = """FELIX
I tried to tell you.
but you wouldn't listen.
and now it's too late.

IVY
It's never too late."""
        result = extract_character_lines(text, "FELIX")
        assert len(result["cue_recall"]) == 1
        line = result["cue_recall"][0]["your_line"]
        assert "wouldn't listen" in line
        assert "too late" in line

    def test_dialogue_starting_with_common_words(self):
        """Lines starting with 'This', 'That', 'What' are dialogue, not action."""
        text = """FELIX
This is exactly what I mean.
That doesn't matter anymore.

IVY
What are you saying?"""
        result = extract_character_lines(text, "FELIX")
        assert len(result["cue_recall"]) == 1
        line = result["cue_recall"][0]["your_line"]
        assert "exactly what I mean" in line
        assert "doesn't matter" in line


class TestParentheticals:
    """Parser must skip parentheticals within dialogue blocks."""

    def test_beat_in_dialogue(self):
        """(beat) inside dialogue should be skipped."""
        text = """FELIX
I don't know what to say.
(beat)
Maybe I should just leave.

IVY
Don't go."""
        result = extract_character_lines(text, "FELIX")
        assert len(result["cue_recall"]) == 1
        line = result["cue_recall"][0]["your_line"]
        assert "(beat)" not in line
        assert "don't know" in line.lower()
        assert "leave" in line.lower()

    def test_pause_in_dialogue(self):
        """(pause) inside dialogue should be skipped."""
        text = """IVY
I need to think about this.
(pause)
Okay, I've decided.

FELIX
And?"""
        result = extract_character_lines(text, "IVY")
        assert len(result["cue_recall"]) == 1
        line = result["cue_recall"][0]["your_line"]
        assert "(pause)" not in line
        assert "decided" in line.lower()


class TestCharacterVariants:
    """Parser must handle character name variants."""

    def test_vo_variant(self):
        text = """FELIX (V.O.)
I remember the first time we met.

IVY
Tell me about it."""
        result = extract_character_lines(text, "FELIX")
        assert len(result["cue_recall"]) == 1
        assert "remember" in result["cue_recall"][0]["your_line"]

    def test_contd_variant(self):
        text = """FELIX
I was saying...

IVY
Go on.

FELIX (CONT'D)
...that we need to talk."""
        result = extract_character_lines(text, "FELIX")
        assert len(result["cue_recall"]) == 2

    def test_os_variant(self):
        text = """FELIX (O.S.)
Hey! Over here!

IVY
Where are you?"""
        result = extract_character_lines(text, "FELIX")
        assert len(result["cue_recall"]) == 1
        assert "Over here" in result["cue_recall"][0]["your_line"]


class TestSceneHeadings:
    """Parser must not treat scene headings as characters."""

    def test_int_ext_headings(self):
        text = """INT. APARTMENT - DAY

FELIX
Good morning.

EXT. PARK - LATER

FELIX
What a beautiful day."""
        result = extract_character_lines(text, "FELIX")
        assert len(result["cue_recall"]) == 2
        for cr in result["cue_recall"]:
            assert "INT." not in cr["cue"]
            assert "EXT." not in cr["cue"]

    def test_episode_markers(self):
        text = """EPISODE 5

INT. KITCHEN - DAY

FELIX
What's for breakfast?"""
        result = extract_character_lines(text, "FELIX")
        assert len(result["cue_recall"]) == 1


class TestCueRecallAccuracy:
    """Cue must always be the previous speaker's last line."""

    def test_first_speaker_gets_scene_start(self):
        text = """FELIX
Opening line.

IVY
Response."""
        result = extract_character_lines(text, "FELIX")
        assert result["cue_recall"][0]["cue"] == "(Scene start)"

    def test_second_speaker_gets_correct_cue(self):
        text = """FELIX
Opening line.

IVY
Response.

FELIX
Second line."""
        result = extract_character_lines(text, "FELIX")
        assert len(result["cue_recall"]) == 2
        assert "IVY" in result["cue_recall"][1]["cue"]
        assert "Response" in result["cue_recall"][1]["cue"]

    def test_three_way_conversation_cues(self):
        text = """FELIX
Hey everyone.

IVY
Hi Felix.

MARCOS
What's up?

FELIX
Not much."""
        result = extract_character_lines(text, "FELIX")
        assert len(result["cue_recall"]) == 2
        assert result["cue_recall"][0]["cue"] == "(Scene start)"
        assert "MARCOS" in result["cue_recall"][1]["cue"]


class TestDenseFormatting:
    """Tests for dense soap/vertical formatting without standard blank-line separation."""

    def test_no_blank_lines_between_speakers(self):
        """Some scripts have no blank lines between character blocks."""
        text = """FELIX
I told you already.
IVY
You didn't.
FELIX
I did. Twice."""
        result = extract_character_lines(text, "FELIX")
        assert len(result["cue_recall"]) == 2
        assert result["cue_recall"][0]["your_line"] == "I told you already."
        assert result["cue_recall"][1]["your_line"] == "I did. Twice."

    def test_action_between_no_blank_lines(self):
        """Action text between speakers without blank lines."""
        text = """FELIX
I'm done.
Ivy stares at him.
IVY
No you're not."""
        result = extract_character_lines(text, "FELIX")
        assert len(result["cue_recall"]) == 1
        assert "stares" not in result["cue_recall"][0]["your_line"]

    def test_page_numbers(self):
        """Page numbers should be ignored."""
        text = """FELIX
First line.

8.

IVY
Second line.

FELIX
Third line."""
        result = extract_character_lines(text, "FELIX")
        assert len(result["cue_recall"]) == 2


class TestEdgeCases:
    """Miscellaneous edge cases."""

    def test_empty_text(self):
        result = extract_character_lines("", "FELIX")
        assert result["cue_recall"] == []
        assert result["chunked_lines"] == []

    def test_empty_character_name(self):
        result = extract_character_lines("FELIX\nHello.", "")
        assert result["cue_recall"] == []

    def test_character_not_in_script(self):
        result = extract_character_lines("FELIX\nHello.\n\nIVY\nHi.", "MARCOS")
        assert result["cue_recall"] == []

    def test_case_insensitive_matching(self):
        text = """FELIX
Hello.

IVY
Hi."""
        result = extract_character_lines(text, "felix")
        assert len(result["cue_recall"]) == 1

    def test_chunking_groups_of_three(self):
        """5 lines should produce 2 chunks: [3, 2]."""
        text = """IVY
First line of dialogue.

FELIX
Response one here.

IVY
Second line of dialogue.

FELIX
Response two here.

IVY
Third line of dialogue.

FELIX
Response three here.

IVY
Fourth line of dialogue.

FELIX
Response four here.

IVY
Fifth line of dialogue.

FELIX
Final response."""
        result = extract_character_lines(text, "IVY")
        # IVY has 5 lines
        assert len(result["cue_recall"]) == 5
        chunks = result["chunked_lines"]
        assert len(chunks) == 2  # [3, 2]
        assert "3 lines" in chunks[0]["chunk_label"]
        assert "2 lines" in chunks[1]["chunk_label"]
