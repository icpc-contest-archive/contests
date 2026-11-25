import unittest

from tools import coverage as CV


def src(url, roles, held=False, **kw):
    s = {"url": url, "roles": roles, **kw}
    if held:
        s["archived"] = ["x/" + url]
    return s


def cov(contests, sets=None):
    return CV.Coverage({"s": {"series": {"id": "s"}, "contests": contests}}, sets or {})


class ResultsTests(unittest.TestCase):
    def rec(self, sources, **kw):
        c = {"id": "s-2001", "sources": sources, **kw}
        return cov([c]).record(c)

    def test_only_the_highest_level_counts(self):
        r = self.rec([src("a", ["rankings"], True), src("b", ["scoreboard"], True), src("c", ["standings"], True)])
        self.assertEqual((r["results"], r["results_known"], r["fetch"]), ("scoreboard", "scoreboard", ""))

    def test_have_means_a_copy_is_held(self):
        r = self.rec([src("a", ["scoreboard"]), src("b", ["standings"], True)])
        self.assertEqual((r["results"], r["results_known"], r["fetch"]), ("standings", "scoreboard", "scoreboard"))

    def test_team_list_is_the_lowest_level(self):
        self.assertEqual(self.rec([src("a", ["teams"], True)])["results"], "teams")
        self.assertEqual(self.rec([src("a", ["teams"], True), src("b", ["rankings"], True)])["results"], "rankings")

    def test_frozen_scoreboard_is_not_on_the_ladder(self):
        r = self.rec([src("a", ["frozen_scoreboard"], True)])
        self.assertEqual((r["results"], r["frozen"]), ("none", "held"))
        r = self.rec([src("a", ["frozen_scoreboard"]), src("b", ["standings"], True)])
        self.assertEqual((r["results"], r["frozen"]), ("standings", "link only"))

    def test_partial(self):
        self.assertTrue(self.rec([src("a", ["scoreboard"], True, scope="top 10")])["partial"])
        self.assertFalse(self.rec([src("a", ["scoreboard"], True, scope="top 10"), src("b", ["scoreboard"], True)])["partial"])
        # a lower level that is whole does not make a partial higher level whole
        self.assertTrue(self.rec([src("a", ["scoreboard"], True, scope="Division 1"), src("b", ["standings"], True)])["partial"])
        # the divisions together are the whole contest
        self.assertFalse(self.rec([src("a", ["scoreboard"], True, scope="Division 1"),
                                   src("b", ["scoreboard"], True, scope="Division 2")])["partial"])


class ProblemTests(unittest.TestCase):
    def rec(self, sources, doc=None, cid="s-2001"):
        c = {"id": cid, "sources": sources}
        sets = {}
        if doc is not None:
            c["problems"] = {"set": "set1"}
            sets["set1"] = {"id": "set1", "contests": [{"contest": cid, **doc.pop("_member", {})}], **doc}
        return cov([c], sets).record(c)

    def test_no_set_no_source(self):
        r = self.rec([])
        self.assertEqual(r["set"], "missing")
        self.assertEqual(set(r["problems"].values()), {"not held"})

    def test_archive_holdings(self):
        r = self.rec([], {"count": 10, "statement": "full", "data": "partial", "solutions": "none", "package": "none"})
        p = r["problems"]
        self.assertEqual((p["statement"], p["data"], p["solutions"], p["package"]), ("all", "some", "not held", "not held"))
        self.assertEqual(r["set"], "count only")

    def test_a_package_implies_statement_data_solutions_not_editorial(self):
        p = self.rec([], {"count": 10, "package": "full"})["problems"]
        self.assertEqual((p["statement"], p["data"], p["solutions"], p["package"], p["editorial"]), ("all", "all", "all", "all", "not held"))
        p = self.rec([src("a", ["problemset"], True, contains=["package"])])["problems"]
        self.assertEqual((p["statement"], p["data"], p["solutions"], p["package"]), ("all", "all", "all", "all"))

    def test_a_held_source_counts_wherever_it_comes_from(self):
        p = self.rec([src("a", ["problemset"], True, contains=["statement"])], {"count": 10, "statement": "none"})["problems"]
        self.assertEqual((p["statement"], p["data"]), ("all", "not held"))

    def test_link_only_and_not_recorded(self):
        p = self.rec([src("a", ["problemset"], False, contains=["statement", "data"])])["problems"]
        self.assertEqual((p["statement"], p["data"], p["solutions"]), ("link only", "link only", "not held"))
        p = self.rec([src("a", ["problemset"], True)])["problems"]   # held, but nobody recorded what it holds
        self.assertEqual(p["statement"], "not recorded")

    def test_a_judge_copy_is_the_list_not_the_material(self):
        p = self.rec([src("a", ["problemset"], True, contains=["statement"], judge="kattis")])["problems"]
        self.assertEqual(p["statement"], "link only")

    def test_single_problems_give_some(self):
        p = self.rec([src("a", ["problem"], True, contains=["statement"])], {"count": 3})["problems"]
        self.assertEqual(p["statement"], "some")
        p = self.rec([src(x, ["problem"], True, contains=["statement"]) for x in "abc"], {"count": 3})["problems"]
        self.assertEqual(p["statement"], "all")

    def test_editorial(self):
        self.assertEqual(self.rec([src("a", ["editorial"], True)])["problems"]["editorial"], "all")
        self.assertEqual(self.rec([src("a", ["editorial"])])["problems"]["editorial"], "link only")

    def test_problem_metadata(self):
        probs = [{"id": "p1", "name": "A", "uuid": "u"}, {"id": "p2", "name": "B", "short_name": "b"}]
        r = self.rec([], {"count": 2, "problems": probs, "_member": {"letters": {"A": "p1"}}})
        self.assertEqual(r["set"], "listed")
        self.assertEqual(r["pmeta"], {"names": "all", "letters": "some", "short_names": "some", "uuids": "some"})

    def test_a_shared_set_reads_every_members_sources(self):
        a = {"id": "s-2001", "problems": {"set": "x"}, "sources": []}
        b = {"id": "s-2002", "problems": {"set": "x"}, "sources": [src("a", ["problemset"], True, contains=["data"])]}
        sets = {"x": {"id": "x", "count": 5, "contests": [{"contest": "s-2001"}, {"contest": "s-2002"}]}}
        self.assertEqual(cov([a, b], sets).record(a)["problems"]["data"], "all")


class WebsiteAndMetadataTests(unittest.TestCase):
    def test_website(self):
        def w(c):
            return cov([c]).record(c)["website"]
        self.assertEqual(w({"id": "s-2001", "sources": [src("a", ["web"], True)]}), "held")
        self.assertEqual(w({"id": "s-2001", "sources": [src("a", ["web"])]}), "no copy")
        self.assertEqual(w({"id": "s-2001"}), "no address")
        self.assertEqual(w({"id": "s-2001", "none": ["web"]}), "none")

    def test_metadata(self):
        a = {"id": "s-2001", "name": "First", "date": "2001-11-03", "cms_ids": [], "parent": None, "next": "s-2002", "sites": [{"location": "se"}]}
        b = {"id": "s-2002", "date": "2002", "next": "s-2004"}
        c = {"id": "s-2003"}
        d = {"id": "s-2004", "cms_ids": [7], "parent": "wf-2005"}
        k = cov([a, b, c, d])
        # what a contest advances to and its neighbouring editions are not coverage: "none" is a valid answer, so they are never missing
        self.assertEqual(k.record(a)["meta"], {"name": "have", "date": "have", "location": "have", "cms": "none"})
        self.assertEqual(k.record(b)["meta"]["date"], "missing")                    # a year is not a full date
        self.assertEqual(k.record(c)["meta"], {"name": "missing", "date": "missing", "location": "missing", "cms": "missing"})
        self.assertEqual(k.record(d)["meta"]["cms"], "have")


class FacetTests(unittest.TestCase):
    def test_every_record_answers_every_facet_with_one_of_its_answers(self):
        c = {"id": "s-2001", "sources": [src("a", ["standings"], True), src("b", ["problemset"], True, contains=["statement"])]}
        r = cov([c]).record(c)
        s = CV.states(r)
        self.assertEqual(list(s), [f[0] for f in CV.FACETS])
        for key, _label, _group, answers, _good in CV.FACETS:
            self.assertIn(s[key], answers)
        self.assertEqual((s["results"], s["statement"], s["website"], s["date"]), ("standings", "all", "no address", "missing"))

    def test_letters_read_off_a_scoreboard_count_without_a_problem_list(self):
        c = {"id": "s-2001", "problems": {"set": "s-2001"}, "sources": []}
        sets = {"s-2001": {"id": "s-2001", "count": 3, "contests": [{"contest": "s-2001", "labels": ["A", "B", "C"]}]}}
        r = cov([c], sets).record(c)
        self.assertEqual((r["set"], r["pmeta"]["letters"], r["pmeta"]["names"]), ("count only", "all", "missing"))

    def test_a_list_as_long_as_its_count_is_complete_whatever_the_flag_says(self):
        doc = {"id": "x", "count": 2, "complete": False, "problems": [{"id": "p-1", "name": "a"}, {"id": "p-2", "name": "b"}]}
        self.assertEqual(CV.set_list_state(doc), "complete")
        self.assertEqual(CV.set_list_state({**doc, "count": 3}), "partial")

    def test_code_is_one_digit_per_facet(self):
        c = {"id": "s-2001", "name": "X", "sources": [src("a", ["scoreboard"], True)]}
        code = CV.encode(cov([c]).record(c))
        self.assertEqual(len(code), len(CV.FACETS))
        self.assertEqual(code[0], "0")                                  # results: scoreboard, the best answer
        self.assertEqual(code[[f[0] for f in CV.FACETS].index("name")], "0")


if __name__ == "__main__":
    unittest.main()
