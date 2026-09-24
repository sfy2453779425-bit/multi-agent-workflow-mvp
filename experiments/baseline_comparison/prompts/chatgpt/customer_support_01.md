TASK
Use the frozen task input below to complete the customer_support task.

INPUT
{
  "query": "Customer says the delivery is late and asks whether the order can be refunded.",
  "user_id": "user_a"
}

CONTEXT / DATA
{
  "shared_context": {},
  "business_data": {
    "default_category": "technical",
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
      },
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
      },
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
          "api"
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

FIXTURE VERSION: customer-support-2026-09-16-v1
FIXTURE SHA256: 19b5bbc3f56d9f049b2a93a7406cb0403a00bd5355f336f62fe448c0d0e33bb4
