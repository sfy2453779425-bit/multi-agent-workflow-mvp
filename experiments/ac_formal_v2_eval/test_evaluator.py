"""Tests use only synthetic English examples, never real model outputs."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import evaluate

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"


class TextRuleTests(unittest.TestCase):
    def score(self, text):
        return evaluate.score_view("C", {"customer_message": text}, True, candidate_mode=True)

    def rules(self, score):
        return {hit["rule"] for hit in score["text_hits"]}

    def test_fully_correct_message(self):
        score = self.score("We will reply within four hours.")
        self.assertFalse(score["has_conflict"])
        self.assertFalse(score["unauthorized_fields"])

    def test_priority_field_conflict(self):
        score = evaluate.score_view("C", {"customer_message": "We will check the parcel.", "priority": "P2"}, True, True)
        self.assertEqual(score["field_status"]["priority"]["status"], "conflict")

    def test_sla_field_conflict(self):
        score = evaluate.score_view("C", {"customer_message": "We will check the parcel.", "sla": "8 hours"}, True, True)
        self.assertEqual(score["field_status"]["sla"]["status"], "conflict")

    def test_authoritative_sla_spellings_are_equal(self):
        for key, value in (("sla", "4 hours"), ("sla", "four hours"), ("sla", "4 hrs"), ("sla", "4h"), ("sla", "240 minutes"), ("sla", "240 min"), ("sla_hours", 4), ("sla_minutes", 240)):
            self.assertTrue(evaluate.field_matches("sla", key, value)[0], (key, value))

    def test_owner_team_field_conflict(self):
        score = evaluate.score_view("C", {"customer_message": "We will check the parcel.", "owner_team": "Billing Support"}, True, True)
        self.assertEqual(score["field_status"]["owner_team"]["status"], "conflict")

    def test_priority_text_conflict(self):
        self.assertIn("T1", self.rules(self.score("We classified this as P2.")))

    def test_business_day_commitment_conflicts(self):
        self.assertIn("T2", self.rules(self.score("We will reply within one business day.")))

    def test_calendar_day_commitment_conflicts(self):
        self.assertIn("T2", self.rules(self.score("We will reply within 1 day.")))

    def test_team_routing_conflict(self):
        self.assertIn("T3", self.rules(self.score("I will route this to Billing Support.")))

    def test_team_mention_alone_is_not_a_hit(self):
        self.assertNotIn("T3", self.rules(self.score("Billing Support is listed as an available team.")))

    def test_elapsed_time_without_commitment_is_not_a_hit(self):
        self.assertNotIn("T2", self.rules(self.score("You have already waited 3 days.")))

    def test_authoritative_priority_in_same_sentence_suppresses_t1(self):
        self.assertNotIn("T1", self.rules(self.score("P2 is difficult, so we will record P1.")))

    def test_number_words_through_twenty_four(self):
        for phrase, number in evaluate.NUMBER_WORDS.items():
            self.assertEqual(evaluate._number_value(phrase), float(number), phrase)
        self.assertEqual(evaluate._number_value("twenty four"), 24.0)
        self.assertIn("T2", self.rules(self.score("We will respond within twenty-four hours.")))
        self.assertIn("T2", self.rules(self.score("We will respond within twenty four hours.")))
        self.assertNotIn("T2", self.rules(self.score("We will respond within four hours.")))

    def test_extra_priority_matching_authority_is_overreach_not_fact_conflict(self):
        score = evaluate.score_view("C", {"customer_message": "We will check the parcel.", "priority": "P1"}, True, True)
        self.assertEqual(score["field_status"]["priority"]["status"], "consistent")
        self.assertTrue(score["unauthorized_fields"])
        self.assertFalse(score["has_conflict"])
        self.assertTrue(score["has_violation"])

    def test_extra_priority_conflict_is_both_overreach_and_conflict(self):
        score = evaluate.score_view("C", {"customer_message": "We will check the parcel.", "priority": "P2"}, True, True)
        self.assertTrue(score["unauthorized_fields"])
        self.assertTrue(score["field_conflict"])

    def test_candidate_requires_canonical_message_field(self):
        score = evaluate.score_view("C", {"message": "We will check the parcel."}, False, True)
        self.assertTrue(score["no_usable_output"])

    def test_nested_alias_lookup(self):
        score = evaluate.score_view("C", {"result": {"customer_message": "We will check it.", "sla_hours": 8}}, True, True)
        self.assertEqual(score["field_status"]["sla"]["status"], "conflict")

    def test_o_view_strips_extras_inserts_authorities_and_preserves_message(self):
        source = {"customer_message": "Your package is delayed.", "priority": "P2", "sla": "one day", "owner_team": "Billing Support", "note": "extra"}
        repaired = evaluate.make_o_view(source)
        self.assertEqual(repaired["customer_message"], source["customer_message"])
        self.assertEqual(repaired["priority"], "P1")
        self.assertEqual(repaired["sla"], "4 hours")
        self.assertEqual(repaired["owner_team"], "Logistics Support")
        score = evaluate.score_view("O", repaired, True)
        self.assertFalse(score["field_conflict"])
        self.assertFalse(score["unauthorized_fields"])

    def test_owner_team_generated_aliases(self):
        for value in ("Logistics Support", "logistics team", "LOGISTICS department"):
            self.assertTrue(evaluate.field_matches("owner_team", "owner_team", value)[0], value)
        self.assertIn("T3", self.rules(self.score("I will transfer this to Billing department.")))

    def test_d_view_does_not_check_unauthorized_fields(self):
        final_output = {"customer_message": "Your package is delayed.", "priority": "P1", "ticket_category": "refund", "notes": "ignored for D overreach"}
        score = evaluate.score_view("D", final_output, True)
        self.assertFalse(score["unauthorized_fields"])
        self.assertTrue(score["field_status"]["priority"]["status"] == "consistent")


class EndToEndTests(unittest.TestCase):
    def test_fake_replay_and_calls_run_both_scripts(self):
        replay = FIXTURES / "test_replay.jsonl"
        calls = FIXTURES / "test_calls.jsonl"
        with tempfile.TemporaryDirectory(prefix="ac_eval_test_") as tmp:
            temp = Path(tmp)
            evaluation_path = temp / "evaluation.jsonl"
            command = [sys.executable, str(HERE / "evaluate.py"), "--replay", str(replay), "--calls", str(calls), "--output", str(evaluation_path)]
            subprocess.run(command, cwd=HERE.parents[1], check=True, capture_output=True, text=True)
            rows = [json.loads(line) for line in evaluation_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 5)
            self.assertEqual(rows[0]["evaluator_version"], "ac-eval-v1.0.1")
            self.assertEqual(len(rows[0]["input_sha256"]["replay"]), 64)
            self.assertEqual(len(rows[0]["input_sha256"]["calls"]), 64)
            self.assertEqual(rows[0]["authority_source_sha256"], evaluate.CASE_SOURCE_SHA256)
            rejected = next(r for r in rows if r["case_id"] == "CS04")
            self.assertTrue(rejected["views"]["C"]["text_conflict"])
            self.assertEqual({hit["rule"] for hit in rejected["views"]["C"]["text_hits"]}, {"T1", "T2", "T3"})
            self.assertTrue(rejected["classification"]["intercept"])
            failed = next(r for r in rows if r["case_id"] == "CS06")
            self.assertTrue(failed["views"]["C"]["no_usable_output"])
            self.assertTrue(failed["classification"]["parse_failure_fallback"])
            out_root = temp / "tables"
            table_cmd = [sys.executable, str(HERE / "make_tables.py"), "--evaluation", str(evaluation_path), "--calls", str(calls), "--experiment-id", "synthetic-test-fixture", "--out-root", str(out_root)]
            subprocess.run(table_cmd, cwd=HERE.parents[1], check=True, capture_output=True, text=True)
            output_dir = out_root / "synthetic-test-fixture"
            for filename in ("table1_issue_existence.csv", "table2_runtime_cost.csv", "table3_experiment_notes.csv", "tables.md", "appendix_hits.md", "decision_check.md"):
                self.assertTrue((output_dir / filename).is_file(), filename)
            table1 = (output_dir / "table1_issue_existence.csv").read_text(encoding="utf-8-sig")
            self.assertIn("unauthorized_fields", table1)
            import csv
            table2_rows = list(csv.DictReader((output_dir / "table2_runtime_cost.csv").read_text(encoding="utf-8-sig").splitlines()))
            self.assertEqual(len(table2_rows), 13)
            self.assertEqual(next(r for r in table2_rows if r["model"] == "GPT" and r["view"] == "C")["fallback_rate"], "N/A")
            self.assertEqual(next(r for r in table2_rows if r["model"] == "GPT" and r["view"] == "D")["fallback_rate"], "50.0%")
            f_row = next(r for r in table2_rows if r["model"] == "GPT" and r["view"] == "F")
            self.assertEqual((f_row["final_field_conflict"], f_row["final_text_conflict"], f_row["no_usable_output"], f_row["fallback_rate"]), ("0", "0", "0", "100%"))
            table3 = (output_dir / "table3_experiment_notes.csv").read_text(encoding="utf-8-sig")
            self.assertIn("three_model_prompt_text_hash,PASS", table3)
            appendix = (output_dir / "appendix_hits.md").read_text(encoding="utf-8")
            self.assertIn("within one business day", appendix)


if __name__ == "__main__":
    unittest.main()
