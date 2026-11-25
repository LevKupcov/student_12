import json
import os
import unittest

from transparent_vacancy.ai import validate
from transparent_vacancy.normalize import normalize
from transparent_vacancy.report import build_report

ROOT = os.path.dirname(os.path.dirname(__file__))
CFG = json.load(open(os.path.join(ROOT, "config.json"), encoding="utf-8"))
ITEMS = json.load(open(os.path.join(ROOT, "data", "sample_api_response.json"), encoding="utf-8"))["results"]["vacancies"]


def topics(rep, vid, kind=None):
    v = next(x for x in rep["vacancies"] if x["id"] == vid)
    return {(i["topic"], i["type"]) for i in v["issues"] if kind is None or i["type"] == kind}


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rep = build_report(ITEMS, CFG)

    def test_dedup_by_id(self):
        self.assertEqual(self.rep["stats"]["vacancies"], 5)

    def test_clean_vacancy_has_empty_array(self):
        v = next(x for x in self.rep["vacancies"] if x["id"] == "demo-005")
        self.assertEqual(v["issues"], [])
        v = next(x for x in self.rep["vacancies"] if x["id"] == "demo-002")
        self.assertEqual(v["issues"], [])

    def test_vague_vacancy(self):
        t = topics(self.rep, "demo-001")
        for need in [("title", "ambiguous"), ("duties", "ambiguous"), ("salary", "ambiguous"),
                     ("schedule", "ambiguous"), ("workplace", "ambiguous")]:
            self.assertIn(need, t)

    def test_contradictions(self):
        t = topics(self.rep, "demo-003", "contradiction")
        self.assertIn(("salary", "contradiction"), t)
        self.assertIn(("schedule", "contradiction"), t)

    def test_missing_has_empty_quote(self):
        v = next(x for x in self.rep["vacancies"] if x["id"] == "demo-004")
        miss = [i for i in v["issues"] if i["type"] == "missing"]
        self.assertTrue(miss and all(i["quote"] == "" for i in miss))

    def test_structured_field_not_repeated_in_text(self):
        # график 5/2 задан в поле, в описании его нет - это не проблема
        self.assertNotIn(("schedule", "missing"), topics(self.rep, "demo-005"))

    def test_ai_hallucinated_quote_dropped(self):
        v = normalize(ITEMS[0])
        bad = [{"topic": "duties", "field": "duty", "quote": "этого нет в тексте", "type": "ambiguous",
                "problem": "x", "recommendation": "y"}]
        good = [{"topic": "duties", "field": "duty", "quote": "Выполнение поручений руководителя", "type": "ambiguous",
                 "problem": "x", "recommendation": "y"}]
        self.assertEqual(validate(bad, v), [])
        self.assertEqual(len(validate(good, v)), 1)


if __name__ == "__main__":
    unittest.main()
