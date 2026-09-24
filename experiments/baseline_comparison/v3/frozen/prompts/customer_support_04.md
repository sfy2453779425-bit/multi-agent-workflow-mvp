TASK
Use the frozen task input below to complete the customer_support task.

INPUT
{
  "query": "The mobile app crashes with an error and is not working after the update.",
  "user_id": "user_a"
}

CONTEXT / DATA
{
  "shared_context": {},
  "business_data": {
    "default_category": "technical",
    "categories": [
      {
        "id": "technical",
        "label": "Technical Issue",
        "keywords": [
          "error",
          "bug",
          "app",
          "website",
          "crash",
          "not working",
          "api",
          "update"
        ],
        "owner_team": "Technical Support",
        "priority": "P2",
        "sla": "1 business day",
        "policy": "Collect reproduction steps and device information, then route to technical support for diagnosis.",
        "next_actions": [
          "Collect reproduction steps.",
          "Ask for device, browser or app version.",
          "Route to technical support with logs if available."
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

FIXTURE VERSION: customer-support-2026-09-16-v2-technical
FIXTURE SHA256: 0cf815ee0ece6249587845067c566974a87345d83519eb743c09374dabb8f001
