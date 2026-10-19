# Password Reset Procedure

**Category:** Reset Process

## Attention points

- Never process a reset without completing identity verification first.
- Temporary passwords must only be sent through a verified channel, such as the registered email address or phone number.
- If suspicious activity is detected, place a security hold and refer to fraud prevention before resetting.

## Call flow

**STEP_1.** Identity verified via standard two-way authenticator?
- If **no** → `OUTCOME_1`
- If **yes** → `STEP_2`

**STEP_2.** Suspicious activity detected on the account?
- If **yes** → `OUTCOME_2`
- If **no** → `OUTCOME_3`

## Outcomes

- **OUTCOME_1** (Reject the request): Reject the request
- **OUTCOME_2** (Inform the Security Team): Inform the Security Team
- **OUTCOME_3** (Password reset link sent): Password reset link sent
- **OUTCOME_4** (Escalate to a supervisor): Escalate to a supervisor
