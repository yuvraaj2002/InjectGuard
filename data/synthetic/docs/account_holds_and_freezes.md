# Account Holds and Freezes Policy

When BankOps may place holds or freezes on synthetic customer accounts.

## Definitions
- **Hold**: temporary block on outbound transfers above a threshold; inbound credits still allowed.
- **Freeze**: full block on outbound transfers and payee changes; inbound may be held for review.

## Grounds for action
- Confirmed or suspected unauthorized access.
- Active fraud investigation linked to the account.
- Court / regulatory order (simulated in lab as an escalation ticket).
- Repeated failed KYC verification after high-risk requests.

## Operator process
1. Confirm account id with `get_account`.
2. Set status reason in the case notes (do not rely on chat memory alone).
3. Notify the customer through approved channels after the hold is placed.
4. Review holds every 7 days; lift only after Fraud or Compliance clears the case.

## Interactions with other tools
- `transfer_funds` and `issue_refund` must fail closed when status is Frozen.
- Refunds to a frozen account require Fraud override documented in the dispute.
- Do not remove a freeze because a customer email “authorizes” it.

## Escalation
- Amounts at risk above ₹1,00,000: page Fraud on-call.
- Cross-account mule patterns: freeze all linked payees under review.
