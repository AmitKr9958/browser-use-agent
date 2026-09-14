# JobPilot production contract

JobPilot is a controlled browser automation layer. Production operation follows these rules:

- Never submit an application automatically.
- Never invent personal, employment, education, salary, authorization, sponsorship, identity, password, OTP, or demographic data.
- Treat CAPTCHA, MFA/OTP, login, payment, and identity-verification gates as blockers unless the user legitimately completes them.
- A browser-agent statement such as `filled` or `saved` is not proof of a successful form change.
- A run is `completed` only when an explicit verification signal is present, such as a verified field value or a verified/visible upload attachment.
- Submission language is a failure/manual-review signal, never a successful application result.
- Agent result text is sanitized before it is returned in an application report to reduce accidental persistence of email addresses, phone numbers, passwords, and verification codes.
- Real authenticated browser acceptance testing must use a user-authorized browser profile or a dedicated test account. Production credentials must never be committed to the repository or passed through source-controlled configuration.
