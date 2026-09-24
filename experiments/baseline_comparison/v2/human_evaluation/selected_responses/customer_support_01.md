# customer_support_01

## Task

Customer says the delivery is late and asks whether the order can be refunded.

## Context

Language: English
Customer query: Customer says the delivery is late and asks whether the order can be refunded.
Relevant frozen policy:
- Category: Delivery / Shipping
  Owner team: Logistics Support
  Priority: P2
  SLA: 1 business day
  Policy: Check tracking status first. If the delivery is delayed beyond the promised window, create a logistics investigation ticket and offer status follow-up.
  Next actions:
  - Confirm order number and tracking status.
  - Open a logistics investigation ticket.
  - Send customer a delivery status response.
- Category: Refund / Return
  Owner team: Billing Support
  Priority: P2
  SLA: 1 business day
  Policy: Check order eligibility and payment status. If eligible, route to billing support for refund processing.
  Next actions:
  - Check refund eligibility.
  - Verify payment transaction status.
  - Route to billing support if refund criteria are met.
Do not invent facts.

## Response A

Ticket classification and routing decision

| Field | Decision |
|---|---|
| Category | Delivery / Shipping (delivery) — primary issue. Refund request is a secondary Refund / Return concern. |
| Owner team | Logistics Support initially; route to Billing Support only if refund eligibility criteria are met. |
| Priority | P2 |
| SLA | 1 business day |
| Policy application | Check the tracking status first. If the delivery is delayed beyond the promised window, create a logistics investigation ticket and provide a status follow-up. Separately, check refund eligibility and payment status; if eligible, route the refund request to Billing Support for processing. |

Next actions

1. Confirm the order number and tracking status.
2. Determine whether the delivery is beyond the promised delivery window.
3. If delayed beyond that window, open a logistics investigation ticket.
4. Check refund eligibility and verify the payment transaction status.
5. If refund criteria are met, route the refund request to Billing Support.
6. Send the customer a delivery status response and explain the refund status based on the eligibility check.

Missing information: The order number, tracking status, promised delivery window, refund eligibility, and payment transaction status were not supplied, so a refund cannot yet be confirmed.

## Response B

[Customer Support Ticket Workflow]
Category: Delivery / Shipping
Intent: refund_or_return
Owner team: Logistics Support
Priority: P2 / SLA: 1 business day

Policy basis:
Check tracking status first. If the delivery is delayed beyond the promised window, create a logistics investigation ticket and offer status follow-up.

Next actions
1. Confirm order number and tracking status.
2. Open a logistics investigation ticket.
3. Send customer a delivery status response.

Response draft: We have classified the issue and routed it to Logistics Support for follow-up.
