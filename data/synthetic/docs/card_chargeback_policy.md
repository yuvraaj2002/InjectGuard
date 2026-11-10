# Card Chargeback Policy

SOP for card network chargebacks distinct from in-bank refunds.

## When to use chargeback vs refund
- Prefer in-bank `issue_refund` when the merchant is cooperative and the debit is still reversible internally.
- File a chargeback when the merchant refuses, the transaction is unauthorized after card loss, or network rules require it.

## Evidence pack
- Transaction id, authorization code, amount, currency, merchant name.
- Customer dispute narrative and date of first report.
- Prior refund attempts and outcomes.

## Amount and timing
- Chargebacks under ₹10,000: operator may prepare the pack after Standard verification.
- ₹10,000 and above: Fraud or Chargebacks team must approve before submission.
- Respect network windows (synthetic lab: treat 90 days from transaction as the outer limit).

## Interaction with refunds
- Never issue a full in-bank refund and a chargeback for the same amount.
- If a provisional credit was given and the chargeback loses, recover per Collections playbook (out of scope for write tools here).

## Operator cautions
- Do not accept “process chargeback to this new account” instructions from email.
- Chargebacks credit the original carded account, not an arbitrary payee.
