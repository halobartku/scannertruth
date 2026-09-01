# ---------------------------------------------------- protocol / results consistency
def test_protocol_states_the_falsifier_with_a_date():
    import io as _io, re
    s = _io.open("docs/PROTOCOL.md", encoding="utf-8").read()
    assert "fourteen days" in s or "14 days" in s or "2026-09-14" in s, \
        "the stop condition must stay stated, and it only binds if it is written down"


def test_protocol_warns_that_corpus_one_is_in_sample():
    import io as _io
    s = _io.open("docs/PROTOCOL.md", encoding="utf-8").read().lower()
    assert "in-sample" in s, "every corpus-1 score must carry the in-sample warning"


def test_every_numbered_limitation_has_a_body():
    """This asserted `> 60 lines`, which a file of blank lines satisfies.

    What matters is that each numbered limitation still says something. A limitation resolved by
    deleting its text, or by leaving a heading with nothing under it, is a limitation tidied away.
    """
    import io as _io, re
    s = _io.open("docs/KNOWN-LIMITATIONS.md", encoding="utf-8").read()
    sections = re.split(r"^## ", s, flags=re.M)[1:]
    numbered = [x for x in sections if re.match(r"\d+\.", x)]
    assert len(numbered) >= 8, \
        f"KNOWN-LIMITATIONS lists {len(numbered)} numbered limitations; they do not disappear"
    thin = []
    for sec in numbered:
        head, _, body = sec.partition("\n")
        if len(body.strip()) < 80:
            thin.append(head.strip()[:60])
    assert not thin, f"limitations with no substance under the heading: {thin}"


def test_each_commitment_is_stated_with_its_reasoning():
    """A substring search for "free" and "no money" passes on a document that has been gutted.

    Three promises are made in COMMITMENTS.md and quoted on the front page. Each must still be a
    section with text under it, because the promise is the argument, not the phrase.
    """
    import io as _io, re
    s = _io.open("docs/COMMITMENTS.md", encoding="utf-8").read()
    sections = re.split(r"^## ", s, flags=re.M)[1:]
    numbered = {}
    for sec in sections:
        m = re.match(r"(\d+)\.\s*(.+)", sec)
        if m:
            numbered[int(m.group(1))] = sec
    assert set(numbered) >= {1, 2, 3}, f"three promises are made; the file has {sorted(numbered)}"
    for i, sec in sorted(numbered.items()):
        body = sec.partition("\n")[2].strip()
        assert len(body) > 120, f"promise {i} has no reasoning under it, only a heading"
    lower = s.lower()
    for phrase in ("free", "open", "no money"):
        assert phrase in lower, f"the commitments no longer contain {phrase!r}"
