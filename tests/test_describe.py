"""The description round: what the checker accepts, and that every stored description is sound."""
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import describe_apply as D  # noqa: E402
import source_descriptions as S  # noqa: E402

GOOD = ("Final scoreboard produced by PC²: 87 teams and nine problems A to I, with attempts and the minute of the accepted run "
        "for each problem, the number solved and the total time. The first twelve places carry a rank.")


def pack(copy=True, earlier=True, roles=("scoreboard",)):
    return {"contest": "x-2000", "sources": [{"n": 1, "url": "http://x/", "roles": list(roles),
                                             "copy": {"path": "x/x-2000/a/page.html"} if copy else None,
                                             "earlier": {"verdict": "confirm"} if earlier and copy else None}]}


def result(**over):
    s = {"n": 1, "verdict": "confirm", "roles": ["scoreboard"], "confidence": "high", "evidence": "table of 87 rows",
         "agrees_with_earlier": True, "disagreement": None, "description": GOOD,
         "document": {"title": "Final", "language": ["en"], "contest_date": "2000-11-11", "teams": 87, "problems": 9,
                      "times": True, "tries": True, "pages": None}}
    s.update(over)
    return {"contest": "x-2000", "sources": [s], "contest_facts": []}


class Check(unittest.TestCase):
    def test_good(self):
        self.assertEqual(D.check(pack(), result()), [])

    def test_no_copy(self):
        self.assertEqual(D.check(pack(copy=False), {"contest": "x-2000", "sources": [{"n": 1, "verdict": "no-copy", "description": None}]}), [])
        self.assertTrue(D.check(pack(copy=False), result()))
        self.assertTrue(D.check(pack(), {"contest": "x-2000", "sources": [{"n": 1, "verdict": "no-copy"}]}))

    def test_description_rules(self):
        for bad in ("This page is a scoreboard of the contest with 87 teams and nine problems, tries and times for each of them, final.",
                    GOOD + " See http://example.org/x for more.",
                    GOOD + " The digest shows only the first rows.",
                    GOOD + " A comprehensive record.",
                    "- " + GOOD,
                    "Short.",
                    "\n\n".join([GOOD] * 4),
                    " ".join([GOOD] * 9)):
            self.assertTrue(D.check(pack(), result(description=bad)), bad[:60])

    def test_not_described_verdicts(self):
        self.assertEqual(D.check(pack(), result(verdict="not-the-document", description=None)), [])
        self.assertTrue(D.check(pack(), result(verdict="wrong-contest")))

    def test_verdict_and_roles(self):
        self.assertTrue(D.check(pack(), result(roles=["standings"])))                      # confirm with other roles
        self.assertTrue(D.check(pack(), result(verdict="correct")))                        # correct with the pack's roles
        self.assertEqual(D.check(pack(), result(verdict="correct", roles=["standings"])), [])
        self.assertTrue(D.check(pack(), result(agrees_with_earlier=None)))
        self.assertTrue(D.check(pack(), result(agrees_with_earlier=False)))               # needs a disagreement
        self.assertEqual(D.check(pack(earlier=False), result(agrees_with_earlier=None)), [])

    def test_document_fields(self):
        for k, v in (("language", "en"), ("contest_date", "11 Nov 2000"), ("teams", "87"), ("times", "yes"), ("title", "x" * 200)):
            r = result()
            r["sources"][0]["document"][k] = v
            self.assertTrue(D.check(pack(), r), k)

    def test_entry_keeps_scoreboard_facts_for_scoreboards_only(self):
        p, r = pack(), result()
        e = D.entry(p["sources"][0], r["sources"][0], "2026-11-16")
        self.assertEqual((e["teams"], e["times"], e["tries"]), (87, True, True))
        r = result(roles=["problemset"], verdict="correct")
        e = D.entry(p["sources"][0], r["sources"][0], "2026-11-16")
        self.assertFalse({"teams", "times", "tries"} & set(e))


class Stored(unittest.TestCase):
    """Every file under data/source-descriptions/ has the shape the site reads, and a description
    that passes the same rules a reader's result has to pass."""

    def test_files(self):
        for f in sorted(S.DIR.glob("*/*.yaml")):
            doc = yaml.safe_load(f.read_text())
            self.assertEqual(doc["contest"], f.stem, f)
            self.assertTrue(f.stem.startswith(f.parent.name + "-") or (ROOT / "series" / f"{f.parent.name}.yaml").exists(), f)
            seen = set()
            for e in doc["sources"]:
                self.assertFalse(set(e) - set(S.FIELDS), f"{f}: unknown field")
                for k in ("url", "read", "rubric", "copy", "description"):
                    self.assertIn(k, e, f)
                self.assertNotIn(e["url"], seen, f)
                seen.add(e["url"])
                self.assertEqual(D.check_description(e["description"]), [], f"{f}: {e['url']}")

    def test_block_renders(self):
        D_ = S.load(fresh=True)
        if not D_:
            self.skipTest("no descriptions yet")
        (cid, _k), e = next(iter(D_.items()))
        html = S.block(e["url"], [{"contest": cid}], "../", lambda c, rel: c, lambda a, rel, t: t)
        self.assertIn('<h2 id="contains">', html)
        self.assertEqual(S.block("http://nowhere.invalid/", [{"contest": cid}], "../", None, None), "")


if __name__ == "__main__":
    unittest.main()
