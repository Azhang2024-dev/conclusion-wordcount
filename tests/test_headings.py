# -*- coding: utf-8 -*-
"""Heading detection rules. Each case below is a real heading shape seen in the corpus."""
import pytest

from wcengine.headings import (backmatter_ok, concl_head_ok, heading_number,
                               is_title_case, simple_head_ok)

PLAIN = ["Conclusion", "Conclusions", "CONCLUSION", "CONCLUDING REMARKS",
         "5 Conclusion", "5. Conclusion", "5: Conclusion", "6. CONCLUSIONS",
         "7 Conclusions and directions", "8. Conclusion; beyond essentialism vs. pluralism",
         "Conclusion: the future of pragmatics", "IMPLICATIONS AND CONCLUDING REMARKS",
         "Discussion and conclusions", "Discussion and conclusion: a decolonial crip project",
         "Conclusions and limitations", "Conclusion and outlook", "Limitations and conclusions",
         "6 CONCLUSION AND OUTLOOK", "5. A conclusion on the analyzability of semantic change"]


@pytest.mark.parametrize("s", PLAIN)
def test_accepts_real_headings(s):
    from wcengine.headings import CONCL_RE
    assert CONCL_RE.match(s) is not None
    assert concl_head_ok(s)


REJECT = ["The conclusion of this study is that the results are unclear",
          "In conclusion, the results show that learners benefited",
          "5.1 Conclusions regarding the first research question were drawn",
          "Conclusions drawn from this study are necessarily limited"]


@pytest.mark.parametrize("s", REJECT)
def test_rejects_prose_starting_with_the_keyword(s):
    assert concl_head_ok(s) is False


def test_heading_number_variants():
    assert heading_number("5 Conclusion") == "5"
    assert heading_number("5.2.1 Results") == "5.2.1"
    assert heading_number("6: Conclusion") == "6"
    assert heading_number("Conclusion") == ""


def test_title_case_helper():
    assert is_title_case("Concluding Remarks and Future Directions")
    assert not is_title_case("Concluding remarks and future directions")


def test_simple_head_ok_rejects_sentence_tails():
    assert simple_head_ok("References")
    assert not simple_head_ok("recommendations.")
    assert not simple_head_ok("Appendix D have provided rich qualitative data")


def test_backmatter_accepts_short_heading_with_period():
    assert backmatter_ok("Appendix A.")
    assert not backmatter_ok("Appendix D have provided rich qualitative data")


@pytest.mark.parametrize("s", ["END NOTES", "End Notes", "ENDNOTES", "Endnote", "Foot notes",
                               "NOTES AND REFERENCES"])
def test_backmatter_matches_spaced_note_headings(s):
    from wcengine.headings import BACKMATTER_RE
    assert BACKMATTER_RE.match(s) is not None


@pytest.mark.parametrize("s", [
    "CRediT authorship contribution statement",
    "CRediT author statement",
    "Funding statement",
    "Authors statement",
    "Author statement",
    "Authorship statement",
    "Author contributions",
    "Notes.",
])
def test_backmatter_matches_elsevier_front_back_matter(s):
    from wcengine.headings import BACKMATTER_RE, backmatter_ok
    assert BACKMATTER_RE.match(s) is not None
    assert backmatter_ok(s)


@pytest.mark.parametrize("s", [
    "452 6. Conclusion and Pedagogical Implications",
    "525 Conclusion",
    "361 5. Discussion",
])
def test_heading_with_page_number_glued_in_front(s):
    assert concl_head_ok(s)
