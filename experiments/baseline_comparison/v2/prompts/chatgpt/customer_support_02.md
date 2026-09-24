TASK
Use the frozen task input below to complete the customer_support task.

INPUT
{
  "query": "Customer requests a refund after being charged twice.",
  "user_id": "user_a"
}

CONTEXT / DATA
{
  "shared_context": {},
  "business_data": {
    "default_category": "refund",
    "categories": [
      {
        "id": "refund",
        "label": "Refund / Return",
        "keywords": [
          "refund",
          "return",
          "cancel",
          "chargeback",
          "money back",
          "payment",
          "charged"
        ],
        "owner_team": "Billing Support",
        "priority": "P2",
        "sla": "1 business day",
        "policy": "Check order eligibility and payment status. If eligible, route to billing support for refund processing.",
        "next_actions": [
          "Check refund eligibility.",
          "Verify payment transaction status.",
          "Route to billing support if refund criteria are met."
        ]
      }
    ]
  }
}

CONSTRAINTS
{
  "apply_frozen_policy": true,
  "do_not_invent_facts": true,
  "required_decisions": [
    "category",
    "route",
    "priority",
    "sla",
    "policy_application"
  ],
  "language": "English"
}

REQUIRED OUTPUT
{
  "required_fields": [
    "category",
    "owner_team",
    "priority",
    "sla",
    "next_actions"
  ],
  "format": "ticket classification, routing decision, SLA, and next actions"
}

MISSING INFORMATION RULE
Do not invent missing facts, data, policy details, weather, inventory, or model metadata. State what is missing when the supplied information is insufficient.

FIXTURE VERSION: customer-support-2026-09-16-v2-refund
FIXTURE SHA256: 614dc169a5f24bcb897851d7f81e85a61146c19e7c815ebce360dfe036516214
