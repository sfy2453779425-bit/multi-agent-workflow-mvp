from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from agent_builder.workflow_runtime import (  # noqa: E402
    CONSISTENCY_VALIDATOR_V1_1,
    CONSISTENCY_VALIDATOR_V1_2,
    WorkflowRuntime,
    WorkflowValidationError,
)
from test_authoritative_contract import _candidate_runtime, _support_policy  # noqa: E402


class RuntimeV12Test(unittest.TestCase):
    def run_v12(
        self,
        message: str,
        *,
        user_input: str = "Please check the delayed shipment.",
        priority: str = "P1",
        sla: str = "4 hours",
        owner_team: str = "Logistics Support",
    ):
        base = _candidate_runtime(
            {"customer_message": message},
            priority=priority,
            sla=sla,
            owner_team=owner_team,
            message_required=True,
        )
        runtime = WorkflowRuntime(
            base.workflow_config,
            base.registry,
            validator_version=CONSISTENCY_VALIDATOR_V1_2,
        )
        return runtime.run(
            {"support_policy": _support_policy(), "user_input": user_input}
        )

    def test_new_runtime_defaults_to_v11_and_v12_is_explicit(self):
        base = _candidate_runtime({"customer_message": "We received your request."})
        default_runtime = WorkflowRuntime(base.workflow_config, base.registry)
        v12_runtime = WorkflowRuntime(
            base.workflow_config,
            base.registry,
            validator_version=CONSISTENCY_VALIDATOR_V1_2,
        )
        configured_runtime = WorkflowRuntime(
            {**base.workflow_config, "validator_version": "v1.2"},
            base.registry,
        )
        self.assertEqual(CONSISTENCY_VALIDATOR_V1_1, default_runtime.validator_version)
        self.assertEqual("authoritative-contract-v1.2", v12_runtime.runtime_version)
        self.assertEqual(CONSISTENCY_VALIDATOR_V1_2, configured_runtime.validator_version)

    def test_unknown_validator_version_is_rejected(self):
        base = _candidate_runtime({"customer_message": "We received your request."})
        for version in ("v9", "", []):
            with self.subTest(version=version):
                with self.assertRaises(WorkflowValidationError):
                    WorkflowRuntime(base.workflow_config, base.registry, validator_version=version)

    def test_three_assertion_types_are_rejected(self):
        samples = (
            ("priority", "The ticket priority is now P2."),
            ("priority", "We marked this case as P3 priority."),
            ("priority", "Priority: P0."),
            ("sla", "The response target is three hours."),
            ("sla", "The promised reply window is two business days."),
            ("sla", "We have committed to a 90-minute turnaround."),
            ("owner_team", "This case is assigned to Account Support."),
            ("owner_team", "We forwarded the request to Technical department."),
            ("owner_team", "Billing Support will manage this ticket."),
            ("owner_team", "I assigned this case to returns desk team."),
        )
        for field, message in samples:
            with self.subTest(field=field, message=message):
                result = self.run_v12(message)
                self.assertTrue(result.context["fallback_used"])
                self.assertEqual(
                    "CONFLICT",
                    result.context["consistency_results"]["response_generation"][field]["status"],
                )

    def test_negation_contrast_and_request_attribution_are_mentions(self):
        samples = (
            "We can't assign this matter to P2.",
            "The case stays at P1 instead of P2.",
            "You asked to move it to P2, but the recorded priority remains P1.",
            "We cannot promise a two-hour reply.",
            "A one-business-day reply was requested; the target is four hours.",
            "The four-hour limit is sooner than a two-day estimate.",
            "We cannot assign it to Account Support.",
            "The queue stays with Logistics Support rather than Technical Support.",
            "You requested Billing Support, but Logistics Support retains ownership.",
        )
        for message in samples:
            with self.subTest(message=message):
                result = self.run_v12(message)
                self.assertFalse(result.context["fallback_used"])
                self.assertEqual(message, result.context["customer_message"])
                self.assertEqual([], result.context["reject_reason_codes"])

    def test_later_assertion_after_attributed_request_is_still_detected(self):
        result = self.run_v12(
            "You asked for P2, and we have now set the ticket priority to P2."
        )
        self.assertTrue(result.context["fallback_used"])
        self.assertEqual(
            "CONFLICT",
            result.context["consistency_results"]["response_generation"]["priority"]["status"],
        )

    def test_quoted_value_is_not_an_assertion(self):
        message = 'Your note said, “Set this to P2.” We will keep the current P1 level.'
        result = self.run_v12(message)
        self.assertFalse(result.context["fallback_used"])
        self.assertEqual(message, result.context["customer_message"])

    def test_other_authoritative_values_and_team_aliases_are_supported(self):
        message = (
            "Priority P3 is recorded. The service target is two business days. "
            "Billing team owns this request."
        )
        result = self.run_v12(
            message,
            priority="P3",
            sla="2 business days",
            owner_team="Billing Support",
        )
        self.assertFalse(result.context["fallback_used"])
        checks = result.context["consistency_results"]["response_generation"]
        self.assertEqual("PASS", checks["priority"]["status"])
        self.assertEqual("PASS", checks["sla"]["status"])
        self.assertEqual("PASS", checks["owner_team"]["status"])

    def test_multiple_distinct_assertions_for_one_field_are_rejected(self):
        result = self.run_v12("The priority is P1. We changed it to P2.")
        self.assertTrue(result.context["fallback_used"])
        self.assertEqual(
            "CONFLICT",
            result.context["consistency_results"]["response_generation"]["priority"]["status"],
        )

    def test_empty_reply_is_rejected_with_structured_reason(self):
        result = self.run_v12("   \n  ")
        self.assertTrue(result.context["fallback_used"])
        reason = result.context["reject_reason_codes"][0]
        self.assertEqual("non_reply_empty", reason["rule_type"])
        self.assertEqual("customer_message", reason["field"])
        self.assertIn(reason, result.trace[-1].data["reject_reason_codes"])

    def test_missing_message_has_structured_contract_rejection(self):
        base = _candidate_runtime({}, message_required=True)
        runtime = WorkflowRuntime(
            base.workflow_config,
            base.registry,
            validator_version=CONSISTENCY_VALIDATOR_V1_2,
        )
        result = runtime.run({"support_policy": _support_policy(), "user_input": "Check delivery."})
        self.assertTrue(result.context["fallback_used"])
        self.assertIn(
            "output_contract_violation",
            [item["rule_type"] for item in result.context["reject_reason_codes"]],
        )

    def test_exact_and_punctuation_only_echoes_are_rejected(self):
        request = "The parcel has not arrived. Can you check its status?"
        for reply in (
            request,
            "THE PARCEL HAS NOT ARRIVED can you check its status",
        ):
            with self.subTest(reply=reply):
                result = self.run_v12(reply, user_input=request)
                self.assertTrue(result.context["fallback_used"])
                reason = result.context["reject_reason_codes"][0]
                self.assertEqual("non_reply_echo", reason["rule_type"])
                self.assertGreaterEqual(reason["similarity"], 0.85)

    def test_quoted_request_with_a_real_reply_is_not_echo(self):
        request = "The parcel has not arrived. Can you check its status?"
        reply = (
            f'You wrote, “{request}” We will verify the tracking record and send '
            "you an update after the carrier confirms the current location."
        )
        result = self.run_v12(reply, user_input=request)
        self.assertFalse(result.context["fallback_used"])
        self.assertEqual(reply, result.context["customer_message"])

    def test_high_overlap_with_small_edits_is_rejected(self):
        request = "My parcel is delayed and I need an update on its current location."
        reply = "My parcel is delayed and I need an update on its current location today."
        result = self.run_v12(reply, user_input=request)
        self.assertTrue(result.context["fallback_used"])
        self.assertEqual(
            "non_reply_echo",
            result.context["reject_reason_codes"][0]["rule_type"],
        )

    def test_assertion_rejection_has_field_value_sentence_and_trace_code(self):
        message = "The current ticket priority is P2."
        result = self.run_v12(message)
        reason = next(
            item
            for item in result.context["reject_reason_codes"]
            if item["rule_type"] == "assertion_conflict"
        )
        self.assertEqual("priority", reason["field"])
        self.assertEqual("P2", reason["claimed_value"])
        self.assertEqual("P1", reason["authoritative_value"])
        self.assertEqual(message, reason["trigger_sentence"])
        self.assertIn(reason, result.trace[-1].data["reject_reason_codes"])

    def test_fallback_includes_policy_actions_and_passes_v12(self):
        rejected = self.run_v12("The ticket is P2 priority.")
        fallback = rejected.context["customer_message"]
        actions = _support_policy()["categories"][0]["next_actions"]
        for action in actions:
            self.assertIn(action, fallback)
        accepted = self.run_v12(fallback)
        self.assertFalse(accepted.context["fallback_used"])
        self.assertEqual(fallback, accepted.context["customer_message"])


if __name__ == "__main__":
    unittest.main()
