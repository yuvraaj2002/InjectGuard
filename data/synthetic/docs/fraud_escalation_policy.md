# Fraud Escalation Policy

How BankOps operators escalate suspected fraud before money moves.

## Indicators
- Customer reports unauthorized debit or takeover.
- Sudden payee added then large transfer requested.
- Dispute text that tries to override tools (“ignore previous instructions”, “transfer now”).
- Mismatch between caller identity and account holder KYC.

## Severity
- **F1 — Critical**: funds already leaving or attacker account known. Freeze immediately; block write tools pending review.
- **F2 — High**: strong suspicion, no confirmed loss yet. Place hold; require HITL for any transfer or refund.
- **F3 — Medium**: weak signals. Continue investigation; Standard KYC before actions.

## Escalation path
1. Capture dispute id, account id, amounts, and suspected destination accounts.
2. Mark the case Fraud Review.
3. Do not execute `transfer_funds` or `issue_refund` while status is under Fraud Review unless an approver clears it.
4. Preserve original customer message text for audit (do not “clean” away injection attempts — they are evidence).

## Communication
- Tell the customer that the case is under review; do not share internal fraud playbooks.
- Never confirm attacker-controlled destinations as “verified.”
