TASK
Use the frozen task input below to complete the customer_support task.

INPUT
{
  "query": "Customer cannot login because the account is locked and needs a password reset.",
  "user_id": "user_a"
}

CONTEXT / DATA
{
  "shared_context": {},
  "business_data": {
    "default_category": "account",
    "categories": [
      {
        "id": "account",
        "label": "Account / Login",
        "keywords": [
          "account",
          "login",
          "password",
          "email",
          "verification",
          "locked"
        ],
        "owner_team": "Account Support",
        "priority": "P3",
        "sla": "2 business days",
        "policy": "Verify customer identity before changing account information or unlocking access.",
        "next_actions": [
          "Ask for identity verification.",
          "Check account lock status.",
          "Provide password reset or unlock instructions."
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

FIXTURE VERSION: customer-support-2026-09-16-v2-account
FIXTURE SHA256: 83a6225518b919e292a47d4f5a81d95d7d4fd2d3ad38eb3b8b8095b3b1451861
