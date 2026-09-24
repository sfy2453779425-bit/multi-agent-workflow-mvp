import copy
import json
import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_builder import (  # noqa: E402
    MockGenerativeNode,
    NodeRegistry,
    NodeExecutionResult,
    WorkflowRuntime,
    WorkflowValidationError,
)
import agent_builder.workflow_runtime as workflow_runtime_module  # noqa: E402
from agent_builder.workflow_runtime import create_authoritative_snapshot  # noqa: E402


def _field(binding, authority, producer, *, grounded_on=None, required=True):
    value = {
        "binding": binding,
        "type": "string",
        "required": required,
        "authority": authority,
        "producer": producer,
    }
    if grounded_on is not None:
        value["grounded_on"] = grounded_on
    return value


def _nodes(*, generative_outputs=None):
    return [
        {
            "id": "classification",
            "type": "classification",
            "mode": "deterministic",
            "outputs": {
                "ticket_category": "context.ticket_category",
                "policy": "context.policy",
            },
        },
        {
            "id": "routing_decision",
            "type": "routing_decision",
            "mode": "deterministic",
            "inputs": {
                "category": "context.ticket_category",
                "policy": "context.policy",
            },
            "outputs": {
                "owner_team": "context.owner_team",
                "priority": "context.priority",
                "sla": "context.sla",
            },
        },
        {
            "id": "response_generation",
            "type": "response_generation",
            "mode": "generative",
            "inputs": {"grounding": "context.authoritative_snapshot"},
            "outputs": generative_outputs or {"customer_message": "context.customer_message"},
        },
    ]


def _fields():
    return {
        "ticket_category": _field("context.ticket_category", "authoritative", "classification"),
        "owner_team": _field("context.owner_team", "authoritative", "routing_decision"),
        "priority": _field("context.priority", "authoritative", "routing_decision"),
        "sla": _field("context.sla", "authoritative", "routing_decision"),
        "customer_message": _field(
            "context.customer_message",
            "generative",
            "response_generation",
            grounded_on=["ticket_category", "owner_team", "priority", "sla"],
            required=False,
        ),
    }


def _v2_config(*, fields=None, nodes=None, include_mode=True, include_contract=True):
    value = {
        "schema_version": 2,
        "runtime_type": "customer_support",
        "workflow_id": "support_contract_test",
        "workflow_name": "Support Contract Test",
        "nodes": copy.deepcopy(nodes or _nodes()),
        "execution": {
            "type": "sequential",
            "order": ["classification", "routing_decision", "response_generation"],
        },
    }
    if include_mode:
        value["workflow_mode"] = "authoritative_contract"
    if include_contract:
        value["output_contract"] = {"fields": copy.deepcopy(fields or _fields())}
    return value


def _runtime(config_value):
    registry = NodeRegistry()
    registry.register(
        "classification",
        lambda context, node_config: {"ticket_category": "delivery", "policy": "support policy"},
    )
    registry.register(
        "routing_decision",
        lambda context, node_config: {
            "owner_team": "Logistics Support",
            "priority": "P1",
            "sla": "1 business day",
        },
    )
    registry.register("response_generation", lambda context, node_config: {})
    return WorkflowRuntime(config_value, registry)


def _candidate_runtime(
    candidate,
    *,
    priority="P1",
    sla="1 business day",
    owner_team="Logistics Support",
    message_required=False,
    grounded_on=None,
):
    fields = _fields()
    fields["customer_message"]["required"] = message_required
    if grounded_on is not None:
        fields["customer_message"]["grounded_on"] = grounded_on
    config_value = _v2_config(fields=fields)
    registry = NodeRegistry()
    registry.register(
        "classification",
        lambda context, node_config: {"ticket_category": "delivery", "policy": "support policy"},
    )
    registry.register(
        "routing_decision",
        lambda context, node_config: {
            "owner_team": owner_team,
            "priority": priority,
            "sla": sla,
        },
    )
    registry.register("response_generation", MockGenerativeNode(candidate))
    return WorkflowRuntime(config_value, registry)


def _support_policy():
    return json.loads((ROOT / "data" / "support_policy.json").read_text(encoding="utf-8"))


def _run_candidate(candidate, **kwargs):
    return _candidate_runtime(candidate, **kwargs).run({"support_policy": _support_policy()})


class SchemaV2ValidationTest(unittest.TestCase):
    def assert_invalid(self, config_value, text):
        with self.assertRaises(WorkflowValidationError) as raised:
            _runtime(config_value).validate({})
        self.assertIn(text, str(raised.exception))

    def test_valid_v1_without_output_contract_keeps_legacy_validation(self):
        registry = NodeRegistry()
        registry.register("echo", lambda context, node_config: {"value": 1})
        config_value = {
            "schema_version": 1,
            "workflow_id": "legacy",
            "workflow_name": "Legacy",
            "runtime_type": "test",
            "nodes": [{"id": "echo", "type": "echo", "outputs": {"value": "context.value"}}],
            "execution": {"type": "sequential", "order": ["echo"]},
        }
        runtime = WorkflowRuntime(config_value, registry)
        runtime.validate({})
        self.assertEqual(1, runtime.run({}).context["value"])

    def test_valid_v2_contract(self):
        _runtime(_v2_config()).validate({})

    def test_missing_authority(self):
        fields = _fields()
        del fields["priority"]["authority"]
        self.assert_invalid(_v2_config(fields=fields), "output_contract.fields.priority")

    def test_missing_producer(self):
        fields = _fields()
        del fields["priority"]["producer"]
        self.assert_invalid(_v2_config(fields=fields), "output_contract.fields.priority")

    def test_producer_node_must_exist(self):
        fields = _fields()
        fields["priority"]["producer"] = "missing_node"
        self.assert_invalid(_v2_config(fields=fields), "missing_node")

    def test_authoritative_field_cannot_use_generative_producer(self):
        fields = _fields()
        fields["priority"]["producer"] = "response_generation"
        self.assert_invalid(_v2_config(fields=fields), "response_generation")

    def test_generative_field_cannot_use_deterministic_producer(self):
        fields = _fields()
        fields["customer_message"]["producer"] = "routing_decision"
        self.assert_invalid(_v2_config(fields=fields), "routing_decision")

    def test_grounded_on_must_reference_existing_field(self):
        fields = _fields()
        fields["customer_message"]["grounded_on"] = ["missing_field"]
        self.assert_invalid(_v2_config(fields=fields), "missing_field")

    def test_grounded_on_cannot_reference_generative_field(self):
        fields = _fields()
        fields["customer_message"]["grounded_on"] = ["customer_message"]
        self.assert_invalid(_v2_config(fields=fields), "generative")

    def test_duplicate_canonical_binding_is_rejected(self):
        fields = _fields()
        fields["category_alias"] = _field(
            "context.ticket_category", "authoritative", "classification"
        )
        self.assert_invalid(_v2_config(fields=fields), "duplicate canonical")

    def test_parent_child_ownership_conflict_is_rejected(self):
        fields = _fields()
        fields["ticket"] = _field("context.ticket", "authoritative", "classification")
        fields["ticket_priority"] = _field(
            "context.ticket.priority", "generative", "response_generation", required=False
        )
        self.assert_invalid(_v2_config(fields=fields), "parent/child")

    def test_v2_requires_workflow_mode(self):
        self.assert_invalid(_v2_config(include_mode=False), "workflow_mode")

    def test_v2_requires_output_contract(self):
        self.assert_invalid(_v2_config(include_contract=False), "output_contract")

    def test_generative_node_cannot_bind_authoritative_final_field(self):
        nodes = _nodes(generative_outputs={"priority": "context.priority"})
        nodes[1]["outputs"].pop("priority")
        self.assert_invalid(_v2_config(nodes=nodes), "generative node")

    def test_field_binding_must_be_declared_by_its_producer(self):
        nodes = _nodes()
        nodes[1]["outputs"].pop("priority")
        self.assert_invalid(_v2_config(nodes=nodes), "binding")

    def test_grounding_producers_must_precede_generative_producer(self):
        config_value = _v2_config()
        config_value["execution"]["order"] = [
            "classification",
            "response_generation",
            "routing_decision",
        ]
        self.assert_invalid(config_value, "execution order")


class CommitGateTest(unittest.TestCase):
    def test_authorized_deterministic_write_is_accepted(self):
        result = _candidate_runtime({}).run({})
        self.assertEqual("P1", result.context["priority"])
        evidence = [item for item in result.context["field_evidence"] if item["field"] == "priority"]
        self.assertEqual(1, len(evidence))
        self.assertTrue(evidence[0]["accepted"])
        self.assertEqual("routing_decision", evidence[0]["attempted_writer"])

    def test_unauthorized_generative_write_is_rejected_and_recorded(self):
        result = _candidate_runtime(
            {
                "priority": "P2",
                "customer_message": "Your case is being handled.",
            }
        ).run({})
        self.assertEqual("P1", result.context["priority"])
        self.assertNotIn("customer_message", result.context)
        candidate_evidence = [
            item
            for item in result.context["field_evidence"]
            if item["attempted_writer"] == "response_generation"
        ]
        self.assertEqual(0, sum(item["accepted"] for item in candidate_evidence))
        priority = next(item for item in candidate_evidence if item["field"] == "priority")
        self.assertEqual("P2", priority["attempted_value"])
        self.assertIn("authoritative", priority["reason"])

    def test_unknown_field_is_rejected(self):
        result = _candidate_runtime({"unknown_field": "x"}).run({})
        self.assertNotIn("unknown_field", result.context)
        evidence = [
            item
            for item in result.context["field_evidence"]
            if item["attempted_writer"] == "response_generation"
        ][0]
        self.assertFalse(evidence["accepted"])
        self.assertIn("unknown", evidence["reason"])

    def test_valid_generative_field_is_accepted(self):
        result = _candidate_runtime(
            {"customer_message": "Your case is being handled by Logistics Support."}
        ).run({})
        self.assertEqual(
            "Your case is being handled by Logistics Support.",
            result.context["customer_message"],
        )
        message = next(
            item for item in result.context["field_evidence"] if item["field"] == "customer_message"
        )
        self.assertTrue(message["accepted"])

    def test_candidate_is_atomic_when_one_write_is_unauthorized(self):
        result = _candidate_runtime(
            {"sla": "1 business day", "customer_message": "We will respond soon."}
        ).run({})
        self.assertNotIn("customer_message", result.context)
        self.assertEqual("1 business day", result.context["sla"])
        candidate_evidence = [
            item
            for item in result.context["field_evidence"]
            if item["attempted_writer"] == "response_generation"
        ]
        self.assertTrue(all(not item["accepted"] for item in candidate_evidence))

    def test_write_sets_are_recorded(self):
        result = _candidate_runtime({"priority": "P2"}).run({})
        write_sets = result.context["write_sets"]["response_generation"]
        self.assertEqual(["customer_message"], write_sets["declared"])
        self.assertEqual(["priority"], write_sets["requested"])
        self.assertEqual([], write_sets["allowed"])

    def test_raw_candidate_is_captured_before_filtering_and_is_immutable(self):
        result = _candidate_runtime({"priority": "P2"}).run({})
        raw = result.context["raw_candidates"]["response_generation"]
        self.assertEqual("P2", raw["priority"])
        with self.assertRaises(TypeError):
            raw["priority"] = "P1"

    def test_empty_candidate_is_supported(self):
        result = _candidate_runtime({}).run({})
        self.assertEqual({}, dict(result.context["raw_candidates"]["response_generation"]))


class ConsistencyValidatorTest(unittest.TestCase):
    def test_priority_pass_conflict_and_unresolved_states(self):
        passed = _run_candidate(
            {"customer_message": "This is P1."}, message_required=True
        )
        conflict = _run_candidate(
            {"customer_message": "This is P2."}, message_required=True
        )
        unresolved = _run_candidate(
            {"customer_message": "We received your request."}, message_required=True
        )
        self.assertEqual(
            "PASS",
            passed.context["consistency_results"]["response_generation"]["priority"]["status"],
        )
        self.assertEqual(
            "CONFLICT",
            conflict.context["consistency_results"]["response_generation"]["priority"]["status"],
        )
        self.assertEqual(
            "UNRESOLVED",
            unresolved.context["consistency_results"]["response_generation"]["priority"]["status"],
        )

    def test_priority_multiple_explicit_claims_are_conflict(self):
        result = _run_candidate(
            {"customer_message": "P1 is urgent, but this is also P2."},
            message_required=True,
        )
        priority = result.context["consistency_results"]["response_generation"]["priority"]
        self.assertEqual("CONFLICT", priority["status"])
        self.assertEqual(["P1", "P2"], priority["claims_found"])

    def test_priority_alias_is_not_guessed(self):
        result = _run_candidate(
            {"customer_message": "This is a high priority request."},
            message_required=True,
        )
        priority = result.context["consistency_results"]["response_generation"]["priority"]
        self.assertEqual("UNRESOLVED", priority["status"])

    def test_sla_pass_conflict_and_unresolved_states(self):
        messages = {
            "four": "We will reply within four hours.",
            "one_business_day": "We will reply within one business day.",
            "twenty_four": "We will reply within 24 hours.",
            "soon": "We will reply soon.",
        }
        results = {
            name: _run_candidate(
                {"customer_message": message},
                priority="P1",
                sla="4 hours",
                message_required=True,
            )
            for name, message in messages.items()
        }
        self.assertEqual(
            "PASS",
            results["four"].context["consistency_results"]["response_generation"]["sla"]["status"],
        )
        self.assertEqual(
            "CONFLICT",
            results["one_business_day"].context["consistency_results"]["response_generation"]["sla"]["status"],
        )
        self.assertEqual(
            "CONFLICT",
            results["twenty_four"].context["consistency_results"]["response_generation"]["sla"]["status"],
        )
        self.assertEqual(
            "UNRESOLVED",
            results["soon"].context["consistency_results"]["response_generation"]["sla"]["status"],
        )

    def test_sla_hour_hyphen_forms_are_normalized(self):
        messages = (
            "We will reply within 4-hour SLA.",
            "We will reply within four-hour SLA.",
            "We will reply within 4-hour.",
            "We will reply within four-hour.",
        )
        for message in messages:
            with self.subTest(message=message):
                result = _run_candidate(
                    {"customer_message": message},
                    priority="P1",
                    sla="4 hours",
                    message_required=True,
                )
                sla = result.context["consistency_results"]["response_generation"]["sla"]
                self.assertEqual("PASS", sla["status"])
                self.assertEqual(["4 hours"], sla["claims_found"])

    def test_sla_business_day_hyphen_forms_are_normalized(self):
        messages = (
            "We will reply within one-business-day.",
            "We will reply within 1-business-day.",
            "We will reply within one-business-day SLA.",
        )
        for message in messages:
            with self.subTest(message=message):
                result = _run_candidate(
                    {"customer_message": message},
                    priority="P1",
                    sla="1 business day",
                    message_required=True,
                )
                sla = result.context["consistency_results"]["response_generation"]["sla"]
                self.assertEqual("PASS", sla["status"])
                self.assertEqual(["1 business day"], sla["claims_found"])

    def test_sla_normalizer_revision_is_explicitly_versioned(self):
        self.assertEqual(
            "authoritative-contract-v1.1",
            getattr(workflow_runtime_module, "WORKFLOW_RUNTIME_VERSION", None),
        )

    def test_sla_multiple_explicit_claims_are_conflict(self):
        result = _run_candidate(
            {"customer_message": "We will reply within 4 hours, within 24 hours."},
            priority="P1",
            sla="4 hours",
            message_required=True,
        )
        sla = result.context["consistency_results"]["response_generation"]["sla"]
        self.assertEqual("CONFLICT", sla["status"])
        self.assertEqual(["4 hours", "24 hours"], sla["claims_found"])

    def test_owner_team_pass_conflict_and_unresolved_states(self):
        messages = {
            "pass": "Logistics Support will handle this.",
            "conflict": "Billing Support will handle this.",
            "unresolved": "Our support team will handle this.",
        }
        results = {
            name: _run_candidate(
                {"customer_message": message}, message_required=True
            )
            for name, message in messages.items()
        }
        self.assertEqual(
            "PASS",
            results["pass"].context["consistency_results"]["response_generation"]["owner_team"]["status"],
        )
        self.assertEqual(
            "CONFLICT",
            results["conflict"].context["consistency_results"]["response_generation"]["owner_team"]["status"],
        )
        self.assertEqual(
            "UNRESOLVED",
            results["unresolved"].context["consistency_results"]["response_generation"]["owner_team"]["status"],
        )

    def test_consistency_aggregation_preserves_individual_states(self):
        mixed = _run_candidate(
            {"customer_message": "This is P1. Logistics Support will handle this."},
            priority="P1",
            sla="4 hours",
            message_required=True,
        )
        unresolved = _run_candidate(
            {"customer_message": "We received your request."},
            priority="P1",
            sla="4 hours",
            message_required=True,
        )
        conflict = _run_candidate(
            {
                "customer_message": (
                    "This is a P2 request. Billing Support will respond within one business day."
                )
            },
            priority="P1",
            sla="4 hours",
            message_required=True,
        )
        mixed_results = mixed.context["consistency_results"]["response_generation"]
        unresolved_results = unresolved.context["consistency_results"]["response_generation"]
        conflict_results = conflict.context["consistency_results"]["response_generation"]
        self.assertEqual("PASS", mixed_results["overall"])
        self.assertEqual("PASS", mixed_results["priority"]["status"])
        self.assertEqual("UNRESOLVED", mixed_results["sla"]["status"])
        self.assertEqual("PASS", mixed_results["owner_team"]["status"])
        self.assertEqual("UNRESOLVED", unresolved_results["overall"])
        self.assertEqual("CONFLICT", conflict_results["overall"])


class AcceptanceGateStage2Test(unittest.TestCase):
    GROUNDED_ON = ["priority", "sla", "owner_team"]
    FALLBACK = (
        "Your request has been assigned to Logistics Support. "
        "Priority: P1. Expected response time: 4 hours."
    )

    def run_stage2(self, candidate):
        return _run_candidate(
            candidate,
            priority="P1",
            sla="4 hours",
            owner_team="Logistics Support",
            message_required=True,
            grounded_on=self.GROUNDED_ON,
        )

    def assert_fallback(self, result):
        context = result.context
        self.assertTrue(context["fallback_used"])
        self.assertEqual(self.FALLBACK, context["customer_message"])
        self.assertEqual("P1", context["priority"])
        self.assertEqual("4 hours", context["sla"])
        self.assertEqual("Logistics Support", context["owner_team"])

    def test_unauthorized_write_uses_fallback(self):
        result = self.run_stage2(
            {"priority": "P2", "customer_message": "We received your request."}
        )
        self.assert_fallback(result)

    def test_unknown_field_uses_fallback(self):
        result = self.run_stage2({"unknown_field": "x", "customer_message": "Hello."})
        self.assert_fallback(result)

    def test_invalid_type_uses_fallback(self):
        result = self.run_stage2({"customer_message": 123})
        self.assert_fallback(result)

    def test_missing_required_message_uses_fallback(self):
        result = self.run_stage2({})
        self.assert_fallback(result)

    def test_sla_conflict_is_rejected_before_commit(self):
        result = self.run_stage2(
            {"customer_message": "We will reply within one business day."}
        )
        self.assert_fallback(result)
        self.assertNotEqual(
            "We will reply within one business day.", result.context["customer_message"]
        )
        self.assertEqual(
            "CONFLICT",
            result.context["consistency_results"]["response_generation"]["sla"]["status"],
        )

    def test_priority_conflict_uses_fallback(self):
        result = self.run_stage2({"customer_message": "This is a P2 request."})
        self.assert_fallback(result)
        self.assertEqual(
            "CONFLICT",
            result.context["consistency_results"]["response_generation"]["priority"]["status"],
        )

    def test_owner_team_conflict_uses_fallback(self):
        result = self.run_stage2({"customer_message": "Billing Support will handle this."})
        self.assert_fallback(result)
        self.assertEqual(
            "CONFLICT",
            result.context["consistency_results"]["response_generation"]["owner_team"]["status"],
        )

    def test_unresolved_message_is_accepted_without_fallback(self):
        message = "We have received your request and will follow up shortly."
        result = self.run_stage2({"customer_message": message})
        self.assertFalse(result.context["fallback_used"])
        self.assertEqual(message, result.context["customer_message"])
        self.assertEqual(
            "UNRESOLVED",
            result.context["consistency_results"]["response_generation"]["overall"],
        )

    def test_fully_consistent_message_is_accepted(self):
        message = "Logistics Support will handle this P1 request within 4 hours."
        result = self.run_stage2({"customer_message": message})
        self.assertFalse(result.context["fallback_used"])
        self.assertEqual(message, result.context["customer_message"])
        self.assertEqual(
            "PASS",
            result.context["consistency_results"]["response_generation"]["overall"],
        )

    def test_adversarial_candidate_rejects_all_three_conflicts_atomically(self):
        result = self.run_stage2(
            {
                "customer_message": (
                    "This is a P2 request. Billing Support will respond within one business day."
                )
            }
        )
        self.assert_fallback(result)
        checks = result.context["consistency_results"]["response_generation"]
        self.assertEqual("CONFLICT", checks["priority"]["status"])
        self.assertEqual("CONFLICT", checks["sla"]["status"])
        self.assertEqual("CONFLICT", checks["owner_team"]["status"])
        self.assertEqual("CONFLICT", checks["overall"])

    def test_field_evidence_contains_grounding_consistency_and_fallback(self):
        result = self.run_stage2({"customer_message": "This is a P2 request."})
        message = next(
            item
            for item in result.context["field_evidence"]
            if item["field"] == "customer_message"
        )
        self.assertEqual(self.GROUNDED_ON, message["grounding_fields"])
        self.assertEqual(
            result.context["grounding_projections"]["response_generation"]["sha256"],
            message["grounding_hash"],
        )
        self.assertEqual(
            "CONFLICT",
            message["consistency_results"]["priority"]["status"],
        )
        self.assertTrue(message["fallback_used"])
        self.assertNotIn("authoritative_facts", message)
        self.assertNotIn("request_context", message)
        self.assertNotIn("canonical_json", message)

    def test_fallback_does_not_reuse_rejected_candidate_text(self):
        secret = "DO NOT LEAK THIS CANDIDATE"
        result = self.run_stage2(
            {"customer_message": f"This is a P2 request. {secret}."}
        )
        self.assert_fallback(result)
        self.assertNotIn(secret, result.context["customer_message"])
        raw = result.context["raw_candidates"]["response_generation"]
        self.assertIn(secret, raw["customer_message"])
        with self.assertRaises(TypeError):
            raw["customer_message"] = "changed"


class AuthoritativeSnapshotTest(unittest.TestCase):
    def test_snapshot_isolated_from_source_context(self):
        source = {"priority": "P1", "nested": {"items": ["one"]}}
        snapshot = create_authoritative_snapshot(source)
        source["priority"] = "P2"
        source["nested"]["items"].append("two")
        self.assertEqual("P1", snapshot.fields["priority"])
        self.assertEqual(("one",), snapshot.fields["nested"]["items"])

    def test_snapshot_nested_values_cannot_be_mutated(self):
        snapshot = create_authoritative_snapshot({"nested": {"value": 1}})
        with self.assertRaises(TypeError):
            snapshot.fields["nested"]["value"] = 2

    def test_snapshot_hash_is_stable_for_same_facts(self):
        first = create_authoritative_snapshot({"b": 2, "a": [1, 2]})
        second = create_authoritative_snapshot({"a": [1, 2], "b": 2})
        self.assertEqual(first.canonical_json, second.canonical_json)
        self.assertEqual(first.sha256, second.sha256)

    def test_grounding_projection_contains_only_declared_facts_and_user_input(self):
        class CapturingHandler:
            def __init__(self):
                self.inputs = None
                self.context = None

            def execute(self, context, node_config):
                self.context = context
                self.inputs = copy.deepcopy(node_config["inputs"])
                return NodeExecutionResult(
                    outputs={"customer_message": "We received your request."},
                    raw_candidate={"customer_message": "We received your request."},
                )

        fields = _fields()
        fields["customer_message"]["grounded_on"] = ["priority", "sla", "owner_team"]
        config_value = _v2_config(fields=fields)
        config_value["nodes"][-1]["inputs"]["user_input"] = "context.user_input"
        handler = CapturingHandler()
        registry = NodeRegistry()
        registry.register(
            "classification",
            lambda context, node_config: {"ticket_category": "delivery", "policy": "support policy"},
        )
        registry.register(
            "routing_decision",
            lambda context, node_config: {
                "owner_team": "Logistics Support",
                "priority": "P1",
                "sla": "4 hours",
            },
        )
        registry.register("response_generation", handler)

        result = WorkflowRuntime(config_value, registry).run(
            {
                "user_input": "Where is my order?",
                "raw_candidates": {"old": "candidate"},
                "field_evidence": [{"debug": "hidden"}],
                "internal_metadata": {"trace_id": "hidden"},
            }
        )

        projection = handler.inputs["grounding"]
        self.assertEqual({}, handler.context)
        self.assertEqual(
            {
                "priority": "P1",
                "sla": "4 hours",
                "owner_team": "Logistics Support",
            },
            projection["authoritative_facts"],
        )
        self.assertEqual({"user_input": "Where is my order?"}, projection["request_context"])
        self.assertNotIn("ticket_category", projection["authoritative_facts"])
        self.assertNotIn("raw_candidates", projection)
        self.assertNotIn("field_evidence", projection)
        self.assertNotIn("internal_metadata", projection)
        self.assertEqual(
            projection["sha256"],
            result.context["grounding_projections"]["response_generation"]["sha256"],
        )

    def test_grounding_projection_hash_matches_for_same_snapshot(self):
        def build_runtime():
            return _candidate_runtime({"customer_message": "We received your request."})

        first = build_runtime().run({"request_id": "one"})
        second = build_runtime().run({"request_id": "two"})
        first_projection = first.context["grounding_projections"]["response_generation"]
        second_projection = second.context["grounding_projections"]["response_generation"]
        self.assertEqual(first_projection["canonical_json"], second_projection["canonical_json"])
        self.assertEqual(first_projection["sha256"], second_projection["sha256"])

    def test_detached_grounding_projection_cannot_change_stored_projection(self):
        class MutatingHandler:
            def execute(self, context, node_config):
                node_config["inputs"]["grounding"]["authoritative_facts"]["priority"] = "P2"
                node_config["inputs"]["grounding"]["fields"]["priority"] = "P2"
                return NodeExecutionResult(
                    outputs={"customer_message": "ok"},
                    raw_candidate={"customer_message": "ok"},
                )

        config_value = _v2_config()
        registry = NodeRegistry()
        registry.register(
            "classification",
            lambda context, node_config: {"ticket_category": "delivery", "policy": "support policy"},
        )
        registry.register(
            "routing_decision",
            lambda context, node_config: {
                "owner_team": "Logistics Support",
                "priority": "P1",
                "sla": "1 business day",
            },
        )
        registry.register("response_generation", MutatingHandler())
        result = WorkflowRuntime(config_value, registry).run({})
        projection = result.context["grounding_projections"]["response_generation"]
        self.assertEqual("P1", projection["authoritative_facts"]["priority"])
        self.assertEqual("P1", projection["fields"]["priority"])
        self.assertEqual("P1", result.context["authoritative_snapshot"].fields["priority"])

    def test_grounding_projection_does_not_duplicate_runtime_debug_state(self):
        result = _candidate_runtime({"customer_message": "We received your request."}).run(
            {"debug": {"node": "response_generation"}}
        )
        projection = result.context["grounding_projections"]["response_generation"]
        self.assertEqual(
            {"request_context", "authoritative_facts", "fields", "canonical_json", "sha256"},
            set(projection),
        )
        self.assertNotIn("debug", projection)
        trace_projection = result.trace[-1].input["grounding"]
        self.assertEqual({"grounding_fields", "grounding_hash"}, set(trace_projection))

    def test_generative_input_is_detached_from_authoritative_snapshot(self):
        class MutatingHandler:
            def execute(self, context, node_config):
                node_config["inputs"]["grounding"]["fields"]["priority"] = "P2"
                return NodeExecutionResult(
                    outputs={"customer_message": "ok"},
                    raw_candidate={"customer_message": "ok"},
                )

        config_value = _v2_config()
        registry = NodeRegistry()
        registry.register(
            "classification",
            lambda context, node_config: {"ticket_category": "delivery", "policy": "support policy"},
        )
        registry.register(
            "routing_decision",
            lambda context, node_config: {
                "owner_team": "Logistics Support",
                "priority": "P1",
                "sla": "1 business day",
            },
        )
        registry.register("response_generation", MutatingHandler())
        result = WorkflowRuntime(config_value, registry).run({})
        self.assertEqual("P1", result.context["priority"])
        self.assertEqual("P1", result.context["authoritative_snapshot"].fields["priority"])


if __name__ == "__main__":
    unittest.main()
