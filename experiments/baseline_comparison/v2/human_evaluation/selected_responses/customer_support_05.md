# customer_support_05

## Task

The delivery is late and I want a refund for the parcel.

## Context

Language: English
Customer query: The delivery is late and I want a refund for the parcel.
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
Mixed-intent precedence: delivery > refund
Do not invent facts.

## Response A

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

## Response B

Ticket classification: Delivery / Shipping

- Category: delivery — Delivery / Shipping
- Owner team: Logistics Support
- Priority: P2
- SLA: 1 business day
- Routing decision: Route to Logistics Support first. The request contains both delivery and refund intents, but the frozen mixed-intent precedence specifies delivery before refund.

Policy application: Check tracking status first. If the parcel is delayed beyond the promised delivery window, create a logistics investigation ticket and provide a status follow-up. A refund cannot be confirmed from the supplied information; refund eligibility and payment status would need to be checked separately under the refund policy.

Next actions:
1. Confirm the order number and tracking status.
2. Determine whether the delivery is beyond the promised delivery window.
3. If so, open a logistics investigation ticket.
4. Send the customer a delivery status response.
5. If refund handling is subsequently required, check refund eligibility and payment transaction status, then route to Billing Support if the refund criteria are met.

Missing information: Order number, current tracking status, promised delivery window, refund eligibility, and payment transaction status are not provided.
