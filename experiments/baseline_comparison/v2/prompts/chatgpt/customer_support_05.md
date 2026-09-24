TASK
Use the frozen task input below to complete the customer_support task.

INPUT
{
  "query": "The delivery is late and I want a refund for the parcel.",
  "user_id": "user_a"
}

CONTEXT / DATA
{
  "shared_context": {},
  "business_data": {
    "default_category": "delivery",
    "categories": [
      {
        "id": "delivery",
        "label": "Delivery / Shipping",
        "keywords": [
          "delivery",
          "shipping",
          "late",
          "delay",
          "parcel",
          "tracking",
          "arrived"
        ],
        "owner_team": "Logistics Support",
        "priority": "P2",
        "sla": "1 business day",
        "policy": "Check tracking status first. If the delivery is delayed beyond the promised window, create a logistics investigation ticket and offer status follow-up.",
        "next_actions": [
          "Confirm order number and tracking status.",
          "Open a logistics investigation ticket.",
          "Send customer a delivery status response."
        ]
      },
      {
        "id": "refund",
        "label": "Refund / Return",
        "keywords": [
          "refund",
          "return",
          "cancel",
          "chargeback",
          "money back",
          "payment"
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
  "mixed_intent_precedence": [
    "delivery",
    "refund"
  ],
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

FIXTURE VERSION: customer-support-2026-09-16-v2-mixed-precedence
FIXTURE SHA256: 08d49825911ae9be8a2594ad38bc123f4ead5b10b486519a31ee2fc01c7b9a59
