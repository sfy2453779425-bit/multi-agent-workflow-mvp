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


MUST_REJECT = (
    ("priority", "This file is a P2 matter.", {}),
    ("priority", "The active code is P3.", {}),
    ("priority", "A P4 level covers this incident.", {}),
    ("priority", "P0 describes the case.", {}),
    ("priority", "Today's case sits at P2.", {}),
    ("priority", "P3 applies to the file.", {}),
    ("priority", "The case is P4.", {}),
    ("priority", "We have a P2 incident today.", {}),
    ("priority", "It falls into P0.", {}),
    ("priority", "P3 is the level currently in use.", {}),
    ("priority", "This request is a P4 case.", {"priority": "P3"}),
    ("priority", "P2 is now active, as requested in the earlier note.", {}),
    ("priority", "The customer asked for P2 and received approval to switch it.", {}),
    ("priority", "The customer's request for P2 was granted after review.", {}),
    ("priority", "We cannot revise the file after a lengthy review, and the case now carries P2.", {}),
    ("priority", "If this incident carries P2 priority, then keep the file open.", {}),
    ("priority", "We cannot change it; P2 is the active classification now.", {}),
    ("priority", "P1 remains recorded—P2 is now selected.", {}),
    ("priority", "The file stays at P1: P2 became the active level.", {}),
    ("priority", "P1 remains set, so P2 is the active label.", {}),
    ("priority", "P1 was not selected because P2 is active.", {}),
    ("priority", "P1 is current rather than P2 or P3.", {}),
    ("priority", "This is not only a P2 issue; it also needs review.", {}),
    ("sla", "The next status update is due in one business day.", {}),
    ("sla", "An answer is expected after two hours.", {}),
    ("sla", "The review will finish in six hours.", {}),
    ("sla", "A written response is scheduled for 30 minutes from now.", {}),
    ("sla", "We will complete the investigation within three days.", {}),
    ("sla", "The support interval here is 24 hours.", {}),
    ("sla", "The review period is two business days.", {}),
    ("sla", "The review period is one hundred and twenty hours.", {}),
    ("sla", "We plan to send the result in 12 hours.", {}),
    ("sla", "This case should close after three business days.", {}),
    ("sla", "A follow-up arrives within five hours.", {}),
    ("sla", "The review finishes in four hours.", {"sla": "2 business days"}),
    ("sla", "A status update will arrive after one business day, as you asked.", {}),
    ("sla", "The next update is due in three days, per your request.", {}),
    ("sla", "The service window is eight hours.", {}),
    ("owner_team", "This case belongs to Billing Support.", {}),
    ("owner_team", "Account Support owns this case.", {}),
    ("owner_team", "Technical Support is the owner here.", {}),
    ("owner_team", "Billing Support has the request.", {}),
    ("owner_team", "Account Support will handle this matter.", {}),
    ("owner_team", "The file is under Technical Support.", {}),
    ("owner_team", "Billing Support is responsible for this record.", {}),
    ("owner_team", "This request sits with Account Support.", {}),
    ("owner_team", "Technical Support will take over.", {}),
    ("owner_team", "We transferred this report to Billing Support.", {}),
    ("owner_team", "We routed the report to Returns Desk Team.", {}),
    ("owner_team", "Kindly transfer the file to Billing Support.", {}),
    ("owner_team", "If the issue is P2, Account Support owns it.", {}),
    ("owner_team", "Per your request, Account Support is now responsible.", {}),
    ("owner_team", "This file rests with Logistics Support.", {"owner_team": "Billing Support"}),
)

MUST_ACCEPT = (
    ("We aren't permitted to classify the report at P2.", {}),
    ("P2 isn't the current classification.", {}),
    ("A P3 is not the selected level.", {}),
    ("We won't move the case into Billing Support.", {}),
    ("The owner isn't Account Support.", {}),
    ("We haven't transferred this to Technical Support.", {}),
    ("We are unable to reclassify the file as P2, P3, or P4.", {}),
    ("It cannot move to Billing Support, Account Support, or Technical Support.", {}),
    ("P1 remains recorded instead of P2.", {}),
    ("The target stays at four hours rather than a one-day allowance.", {}),
    ("The customer's note requested P2; the record remains P1.", {}),
    ("The customer's message asked for Billing Support; Logistics Support still owns the case.", {}),
    ("Your email requested a one-business-day reply; the actual target is four hours.", {}),
    (
        "You wrote, ‘Please assign this report to Billing Support until tomorrow.’ "
        "We will leave ownership with Logistics Support while we inspect the delivery scan.",
        {"user_input": "Please assign this report to Billing Support until tomorrow."},
    ),
    ("Logistics Support is assigned the P1 case with a four-hour response target.", {}),
    ("Our delivery team is reviewing carrier records.", {}),
    ("The shipping team is checking the dispatch scan.", {}),
    ("Our customer care team is reviewing the account notes.", {}),
    ("The parcel's trip took three days to reach the sorting center.", {}),
    ("Payment settled after six hours.", {}),
    ("The package arrived two days ago.", {}),
    ("The parcel has been in transit for the past three days.", {}),
    ("The refund appeared in your account five days ago.", {}),
    ("The carrier has held the parcel since yesterday, three days ago.", {}),
    ("Delivery may take 36 hours after dispatch.", {}),
    ("Parcel delivery took two days; the help desk will answer in four hours.", {}),
    ("A one-day delivery window was estimated for this order.", {}),
    ("The owner is Logistics Support, and priority P1 remains recorded.", {}),
    ("P1 applies—P2 is not in effect.", {}),
    ("P1 is current: P2 is not active.", {}),
    ("The ticket remains P1, so P2 is not selected.", {}),
    ("The incident is P1; P2 was never activated.", {}),
    ("P1 is set, then P2 is not considered.", {}),
    ("Because P2 is not active, the file remains at P1.", {}),
)

ROUND3_ATTRIBUTED_FULFILLMENT_REJECT = (
    ("priority", "The customer's message asked for P2, and that level was approved.", {}),
    ("priority", "You wanted P2, so I've updated it.", {}),
    ("priority", "Your email requested P3. That level was selected.", {}),
    ("priority", "The customer asked for P4; we approved that classification.", {}),
    ("priority", "You asked for P3. We switched the active level.", {}),
    ("owner_team", "You asked for Billing Support, and we've taken care of that.", {}),
    ("owner_team", "The customer requested Account Support. We routed the case there.", {}),
    ("owner_team", "Your message wanted Technical Support; that group now owns the case.", {}),
    ("owner_team", "The email asked for Billing Support, so we moved the case to that queue.", {}),
    ("sla", "You requested a response after two days; we set that interval.", {}),
    ("sla", "Your note asked for six hours. We now guarantee that timing.", {}),
    ("sla", "The customer wanted a one-day reply, and we changed the target.", {}),
    ("sla", "Your message requested 30 minutes, then we approved that window.", {}),
    ("sla", "The email sought three days for a response; that schedule is now in place.", {}),
)

ROUND3_NEGATED_FULFILLMENT_SAFE = (
    "You asked for P2, but we're unable to change the priority entry.",
    "Your email requested Billing Support; we cannot route the case there.",
    "The note asked for a one-day response, but we won't change the service target.",
    "You wanted P3. That adjustment wasn't approved.",
    "The customer asked for Account Support, though we haven't moved ownership.",
)

ROUND3_AUTHORITATIVE_RESTATEMENT_SAFE = (
    "You asked to label this P2, but the active priority remains P1.",
    "Your message requested Billing Support; Logistics Support remains responsible.",
    "You sought a one-day turnaround, but our response target is four hours.",
    "Your email asked for Technical Support; the case stays with Logistics Support.",
    "The customer requested P4, but we confirmed that P1 remains active.",
)

ROUND3_OTHER_OBJECT_SAFE = (
    "You requested P2, and we added your comment to the case file.",
    "The customer asked for Billing Support; we approved the attached invoice.",
    "Your message requested P3. We updated the spreadsheet for audit purposes.",
    "You wanted a two-day response, and we sorted the shipment photographs.",
    "The note asked for Technical Support; we completed the carrier summary.",
)

ROUND3_OTHER_PROCESS_DURATION_SAFE = (
    "The card refund usually appears in five business days.",
    "A bank deposit can take two days to post.",
    "Reimbursement funds may reach the account within 48 hours.",
    "The returned payment should clear after three business days.",
    "Bank processing for a charge reversal can last six hours.",
)

ROUND3_RESPONSE_DEADLINE_REJECT = (
    "We'll reply about the refund within one business day.",
    "Our agent will respond about the bank deposit in three hours.",
    "We will get back to you about the reimbursement within two days.",
    "A support response regarding the card credit should reach you after six hours.",
    "We'll follow up about your refund within 30 minutes.",
)

ROUND3_EXPLICIT_SLA_WITH_PROCESS_CONTEXT = (
    "The delivery ticket has a 4-hour SLA while tracking is reviewed.",
    "This shipment case carries a four-hour service-level target.",
    "The parcel inquiry remains under an SLA of 4 hours during transit checks.",
    "Our delivery request has a service level of four hours.",
    "The package issue is tracked against a 4-hour SLA despite the carrier delay.",
)


class RuntimeV12Test(unittest.TestCase):
    def run_version(
        self,
        message: str,
        *,
        version: str = CONSISTENCY_VALIDATOR_V1_2,
        user_input: str = "Please check the delayed shipment.",
        priority: str = "P1",
        sla: str = "4 hours",
        owner_team: str = "Logistics Support",
        category: str | None = None,
    ):
        base = _candidate_runtime(
            {"customer_message": message},
            priority=priority,
            sla=sla,
            owner_team=owner_team,
            message_required=True,
        )
        if category is not None:
            base.registry.register(
                "classification",
                lambda context, node_config: {
                    "ticket_category": category,
                    "policy": "Use the selected support category.",
                },
                replace=True,
            )
        runtime = WorkflowRuntime(base.workflow_config, base.registry, validator_version=version)
        return runtime.run(
            {"support_policy": _support_policy(), "user_input": user_input}
        )

    def run_v12(self, message: str, **kwargs):
        return self.run_version(message, **kwargs)

    def test_new_runtime_defaults_to_v11_and_v12_is_explicit(self):
        base = _candidate_runtime({"customer_message": "The carrier scan is under review."})
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
        self.assertEqual("authoritative-contract-v1.1", default_runtime.runtime_version)
        self.assertEqual("authoritative-contract-v1.2", v12_runtime.runtime_version)
        self.assertEqual(CONSISTENCY_VALIDATOR_V1_2, configured_runtime.validator_version)
        legacy_result = default_runtime.run({"support_policy": _support_policy()})
        self.assertNotIn("runtime_version", legacy_result.context)
        self.assertNotIn("validator_version", legacy_result.trace[-1].data)

    def test_unknown_validator_version_is_rejected(self):
        base = _candidate_runtime({"customer_message": "We received your request."})
        for version in ("v9", "v1.3", "", []):
            with self.subTest(version=version):
                with self.assertRaises(WorkflowValidationError):
                    WorkflowRuntime(base.workflow_config, base.registry, validator_version=version)

    def test_three_assertion_types_are_rejected(self):
        samples = (
            ("priority", "This file carries the P2 classification."),
            ("priority", "The incident has a P3 level."),
            ("priority", "P0 applies to this request."),
            ("sla", "The next review is due in one business day."),
            ("sla", "A response is planned after six hours."),
            ("sla", "The support period is three days."),
            ("owner_team", "The case is with Account Support."),
            ("owner_team", "Technical Support owns the request."),
            ("owner_team", "Billing Support is responsible for this record."),
            ("owner_team", "We routed the file to Returns Desk Team."),
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
            "We aren't permitted to classify the report at P2.",
            "P1 remains recorded instead of P2.",
            "The customer's message asked for P2; the record remains P1.",
            "One day is not the promised interval.",
            "You mentioned a delayed answer; our target remains four hours.",
            "The target stays at four hours rather than a one-day allowance.",
            "We haven't transferred this to Account Support.",
            "The case stays with Logistics Support rather than Technical Support.",
            "Your email requested Billing Support; Logistics Support still owns the case.",
        )
        for message in samples:
            with self.subTest(message=message):
                result = self.run_v12(message)
                self.assertFalse(result.context["fallback_used"])
                self.assertEqual(message, result.context["customer_message"])
                self.assertEqual([], result.context["reject_reason_codes"])

    def test_later_assertion_after_attributed_request_is_still_detected(self):
        result = self.run_v12(
            "The customer's note asked to use P2; then P2 was selected as the active level."
        )
        self.assertTrue(result.context["fallback_used"])
        self.assertEqual(
            "CONFLICT",
            result.context["consistency_results"]["response_generation"]["priority"]["status"],
        )

    def test_quoted_value_is_not_an_assertion(self):
        user_input = "Please keep this request with Billing Support until noon."
        message = (
            'The message said, “Please keep this request with Billing Support until noon.” '
            "Logistics Support remains responsible while we inspect the scan history."
        )
        result = self.run_v12(message, user_input=user_input)
        self.assertFalse(result.context["fallback_used"])
        self.assertEqual(message, result.context["customer_message"])

    def test_other_authoritative_values_and_team_aliases_are_supported(self):
        message = (
            "The case remains at P3. The review commitment is two business days. "
            "Billing team owns the record."
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
        result = self.run_v12("The file is P1. We moved its priority to P2.")
        self.assertTrue(result.context["fallback_used"])
        self.assertEqual(
            "CONFLICT",
            result.context["consistency_results"]["response_generation"]["priority"]["status"],
        )

    def test_empty_reply_is_rejected_with_structured_reason(self):
        result = self.run_v12("\u2003 \n \t")
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
        result = runtime.run({"support_policy": _support_policy(), "user_input": "Review the shipment record."})
        self.assertTrue(result.context["fallback_used"])
        self.assertIn(
            "output_contract_violation",
            [item["rule_type"] for item in result.context["reject_reason_codes"]],
        )

    def test_exact_and_punctuation_only_echoes_are_rejected(self):
        request = "My order tracking page has not refreshed since Thursday afternoon; could someone review it?"
        for reply in (
            request,
            "MY ORDER TRACKING PAGE HAS NOT REFRESHED SINCE THURSDAY AFTERNOON could someone review it",
        ):
            with self.subTest(reply=reply):
                result = self.run_v12(reply, user_input=request)
                self.assertTrue(result.context["fallback_used"])
                reason = result.context["reject_reason_codes"][0]
                self.assertEqual("non_reply_echo", reason["rule_type"])
                self.assertGreaterEqual(reason["similarity"], 0.85)

    def test_quoted_request_with_a_real_reply_is_not_echo(self):
        request = "The tracking page has shown no movement since Monday; could you investigate?"
        reply = (
            f'Your message said, “{request}” We will review the carrier events and send '
            "you an update after checking the latest scan."
        )
        result = self.run_v12(reply, user_input=request)
        self.assertFalse(result.context["fallback_used"])
        self.assertEqual(reply, result.context["customer_message"])

    def test_high_overlap_with_small_edits_is_rejected(self):
        request = "The tracking page has shown no movement since Monday; could you investigate?"
        reply = "The tracking page has shown no movement since Monday; could you investigate today?"
        result = self.run_v12(reply, user_input=request)
        self.assertTrue(result.context["fallback_used"])
        self.assertEqual(
            "non_reply_echo",
            result.context["reject_reason_codes"][0]["rule_type"],
        )

    def test_assertion_rejection_has_field_value_sentence_and_trace_code(self):
        message = "The active classification for this report is P2."
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
        rejected = self.run_v12("This report is currently P2.")
        fallback = rejected.context["customer_message"]
        actions = _support_policy()["categories"][0]["next_actions"]
        self.assertTrue(any(action in fallback for action in actions))
        self.assertTrue(rejected.trace[-1].data["fallback_self_check"]["passed"])
        accepted = self.run_v12(fallback)
        self.assertFalse(accepted.context["fallback_used"])
        self.assertEqual(fallback, accepted.context["customer_message"])
        self.assertIn("Next steps our team will take:", fallback)
        self.assertTrue(_support_policy()["categories"][0]["next_actions"])

    def test_all_literal_wrong_value_samples_are_rejected(self):
        self.assertGreaterEqual(len(MUST_REJECT), 30)
        for field, message, kwargs in MUST_REJECT:
            with self.subTest(field=field, message=message):
                result = self.run_v12(message, **kwargs)
                self.assertTrue(result.context["fallback_used"])
                self.assertEqual(
                    "CONFLICT",
                    result.context["consistency_results"]["response_generation"][field]["status"],
                )

    def test_all_literal_safe_samples_are_accepted(self):
        self.assertGreaterEqual(len(MUST_ACCEPT), 20)
        for message, kwargs in MUST_ACCEPT:
            with self.subTest(message=message):
                result = self.run_v12(message, **kwargs)
                self.assertFalse(result.context["fallback_used"])
                self.assertEqual(message, result.context["customer_message"])

    def test_synthetic_wrong_value_corpus_covers_all_fields_without_cues(self):
        self.assertEqual({"priority", "sla", "owner_team"}, {sample[0] for sample in MUST_REJECT})
        cue_words = (
            "mark", "set", "chang", "updat", "rais", "lower", "escalat", "reply",
            "respond", "response", "hear from", "target", "turnaround", "sla", "promis",
            "expect", "commit", "assign", "rout", "forward", "transfer", "manag", "handl",
            "owner", "own", "responsible", "queue", "stay", "remain", "send", "sent",
            "pass", "direct",
        )
        without_cues = [
            sample for sample in MUST_REJECT
            if not any(cue in sample[1].casefold() for cue in cue_words)
        ]
        self.assertGreaterEqual(len(without_cues), (len(MUST_REJECT) + 1) // 2)

    def test_partial_user_input_echo_is_rejected(self):
        request = "Could you route this report to Billing Support before the morning review?"
        reply = "route this report to Billing Support"
        result = self.run_v12(reply, user_input=request)
        self.assertTrue(result.context["fallback_used"])
        reason = result.context["reject_reason_codes"][0]
        self.assertEqual("non_reply_echo", reason["rule_type"])
        self.assertGreaterEqual(reason["overlap_chars"], 20)

    def test_quote_only_exempts_text_present_in_user_input(self):
        message = 'The note says “P2 was approved.” The active level remains P1.'
        result = self.run_v12(message, user_input="Please check the delivery status.")
        self.assertTrue(result.context["fallback_used"])
        self.assertEqual(
            "CONFLICT",
            result.context["consistency_results"]["response_generation"]["priority"]["status"],
        )

    def test_unknown_team_requires_a_local_assignment_verb(self):
        mention = self.run_v12("The regional care team is reviewing the carrier notes.")
        routed = self.run_v12("We escalated this case to the regional care team.")
        self.assertFalse(mention.context["fallback_used"])
        self.assertTrue(routed.context["fallback_used"])
        self.assertEqual(
            "CONFLICT",
            routed.context["consistency_results"]["response_generation"]["owner_team"]["status"],
        )

    def test_fallback_filters_category_action_conflicting_with_authoritative_team(self):
        rejected = self.run_v12(
            "This report is P2.",
            owner_team="Logistics Support",
            category="refund",
        )
        fallback = rejected.context["customer_message"]
        self.assertTrue(rejected.context["fallback_used"])
        self.assertIn("Next steps our team will take:", fallback)
        self.assertNotIn("Billing Support", fallback)
        self.assertTrue(rejected.trace[-1].data["fallback_self_check"]["passed"])
        filtered = rejected.context["fallback_self_check"]["filtered_actions"]
        self.assertTrue(any("billing support" in item["action"].casefold() for item in filtered))
        accepted = self.run_v12(fallback, owner_team="Logistics Support", category="refund")
        self.assertFalse(accepted.context["fallback_used"])

    def test_fallback_with_matching_category_team_keeps_a_next_step(self):
        rejected = self.run_v12(
            "The recorded owner is Logistics Support.",
            owner_team="Billing Support",
            category="refund",
        )
        fallback = rejected.context["customer_message"]
        self.assertTrue(rejected.context["fallback_used"])
        self.assertIn("Next steps our team will take:", fallback)
        self.assertIn("Billing Support", fallback)
        self.assertTrue(rejected.trace[-1].data["fallback_self_check"]["passed"])

    def test_fallback_self_check_uses_minimal_version_when_actions_make_echo(self):
        user_input = (
            "Your inquiry has been assigned to Logistics Support. Priority: P1. "
            "Expected response time: 4 hours.\nNext steps our team will take:\n"
            "- Confirm order number and tracking status.\n"
            "- Open a logistics investigation ticket.\n"
            "- Send customer a delivery status response."
        )
        result = self.run_v12("This report is P2.", user_input=user_input)
        self.assertTrue(result.context["fallback_self_check"]["used_minimal_fallback"])
        self.assertTrue(result.context["fallback_self_check"]["passed"])
        self.assertNotIn("Next steps our team will take:", result.context["customer_message"])

    def test_v12_generation_trace_and_context_include_runtime_versions(self):
        result = self.run_v12("We will check the recent carrier scans.")
        self.assertEqual("authoritative-contract-v1.2", result.context["runtime_version"])
        self.assertEqual(CONSISTENCY_VALIDATOR_V1_2, result.context["validator_version"])
        generation_trace = next(
            item for item in result.trace if item.node_id == "response_generation"
        )
        self.assertEqual("authoritative-contract-v1.2", generation_trace.data["runtime_version"])
        self.assertEqual(CONSISTENCY_VALIDATOR_V1_2, generation_trace.data["validator_version"])

    def test_round3_restores_two_replaced_regression_samples(self):
        reject = self.run_v12(
            "The customer's message asked for P2, and that level was approved."
        )
        self.assertTrue(reject.context["fallback_used"])
        self.assertEqual(
            "CONFLICT",
            reject.context["consistency_results"]["response_generation"]["priority"]["status"],
        )

        accept = self.run_v12("A one-day reply is not the promised interval.")
        self.assertFalse(accept.context["fallback_used"])
        self.assertEqual("A one-day reply is not the promised interval.", accept.context["customer_message"])

    def test_round3_attributed_values_followed_by_fulfillment_are_conflicts(self):
        self.assertGreaterEqual(len(ROUND3_ATTRIBUTED_FULFILLMENT_REJECT), 5)
        for field, message, kwargs in ROUND3_ATTRIBUTED_FULFILLMENT_REJECT:
            with self.subTest(field=field, message=message):
                result = self.run_v12(message, **kwargs)
                self.assertTrue(result.context["fallback_used"])
                self.assertEqual(
                    "CONFLICT",
                    result.context["consistency_results"]["response_generation"][field]["status"],
                )

    def test_round3_negated_followthrough_does_not_cancel_attribution_exemption(self):
        self.assertGreaterEqual(len(ROUND3_NEGATED_FULFILLMENT_SAFE), 5)
        for message in ROUND3_NEGATED_FULFILLMENT_SAFE:
            with self.subTest(message=message):
                result = self.run_v12(message)
                self.assertFalse(result.context["fallback_used"])

    def test_round3_authoritative_restatement_preserves_attribution_exemption(self):
        self.assertGreaterEqual(len(ROUND3_AUTHORITATIVE_RESTATEMENT_SAFE), 5)
        for message in ROUND3_AUTHORITATIVE_RESTATEMENT_SAFE:
            with self.subTest(message=message):
                result = self.run_v12(message)
                self.assertFalse(result.context["fallback_used"])

    def test_round3_followthrough_about_a_different_object_preserves_attribution(self):
        self.assertGreaterEqual(len(ROUND3_OTHER_OBJECT_SAFE), 5)
        for message in ROUND3_OTHER_OBJECT_SAFE:
            with self.subTest(message=message):
                result = self.run_v12(message)
                self.assertFalse(result.context["fallback_used"])

    def test_round3_refund_and_bank_processing_durations_are_not_sla_claims(self):
        safe_messages = ROUND3_OTHER_PROCESS_DURATION_SAFE + (
            "A one-day reply is not the promised interval.",
        )
        self.assertGreaterEqual(len(safe_messages), 5)
        for message in safe_messages:
            with self.subTest(message=message):
                result = self.run_v12(message)
                self.assertFalse(result.context["fallback_used"])

    def test_round3_reply_deadlines_about_financial_processes_remain_sla_claims(self):
        self.assertGreaterEqual(len(ROUND3_RESPONSE_DEADLINE_REJECT), 5)
        for message in ROUND3_RESPONSE_DEADLINE_REJECT:
            with self.subTest(message=message):
                result = self.run_v12(message)
                self.assertTrue(result.context["fallback_used"])
                self.assertEqual(
                    "CONFLICT",
                    result.context["consistency_results"]["response_generation"]["sla"]["status"],
                )

    def test_round3_explicit_sla_is_not_misclassified_as_other_process_duration(self):
        self.assertGreaterEqual(len(ROUND3_EXPLICIT_SLA_WITH_PROCESS_CONTEXT), 5)
        for message in ROUND3_EXPLICIT_SLA_WITH_PROCESS_CONTEXT:
            with self.subTest(message=message):
                result = self.run_v12(message)
                self.assertFalse(result.context["fallback_used"])
                self.assertEqual(
                    "PASS",
                    result.context["consistency_results"]["response_generation"]["sla"]["status"],
                )


if __name__ == "__main__":
    unittest.main()
