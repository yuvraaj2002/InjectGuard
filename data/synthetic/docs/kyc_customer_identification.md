# KYC and Customer Identification Policy

Know Your Customer (KYC) rules for BankOps when verifying identity before high-risk actions.

## When KYC re-check is required
- First-time payee addition above ₹1,00,000 cumulative in 24 hours.
- Refund or transfer requests that change destination accounts.
- Account status changes from Frozen / Restricted back to Active.
- Customer claims of unauthorized access or SIM swap.

## Verification levels
- **Basic**: name + registered mobile OTP (already completed at onboarding).
- **Standard**: Basic plus last 4 digits of PAN / government id on file.
- **Enhanced**: Standard plus live video KYC or branch attestation for amounts above ₹5,00,000.

## Operator checklist
1. Confirm account holder name matches the dispute or request.
2. Do not accept identity documents pasted only in email bodies.
3. If KYC is incomplete, refuse money-moving tools and create an escalation note.
4. Never ask the customer to share full card PAN, CVV, or internet banking password in chat.

## Red flags
- Customer asks to skip KYC “just this once.”
- Requestor name differs from account holder.
- Sudden change of contact email followed by a large transfer request.
