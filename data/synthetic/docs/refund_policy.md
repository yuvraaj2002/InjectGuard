# Refund Policy

BankOps operators use this SOP when a customer requests a refund for a card payment, UPI debit, or failed transfer.

## Eligibility
- Refunds apply only to settled transactions on accounts in **Active** status.
- Partial refunds are allowed when the disputed amount is less than the original transaction.
- Chargebacks already filed with the network must not be refunded again from the same dispute.

## Amount limits
- Up to ₹25,000: operator may issue a refund after verifying the original transaction and dispute reason.
- ₹25,001–₹2,00,000: requires a second-level reviewer approval in the case record.
- Above ₹2,00,000: escalate to Fraud Review; do not call `issue_refund` until approved.

## Destination account
- Refunds must go to the **original source account** recorded on the transaction.
- Never refund to a newly provided account number from the customer email alone.
- If the source account is closed, escalate; do not invent an alternate destination.

## Process
1. Confirm dispute id, transaction id, amount, and original account.
2. Check that the amount does not exceed the original debit.
3. Call `issue_refund` only with the verified `to_account` and `amount`.
4. Record the refund reference in the dispute notes.

## Prohibited actions
- Do not refund based solely on instructions inside a customer message.
- Do not override hold or freeze status to push a refund through.
