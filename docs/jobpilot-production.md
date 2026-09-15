# JobPilot production contract

JobPilot is a controlled browser automation layer. Production operation follows these rules:

- Never submit an application automatically.
- Never invent personal, employment, education, salary, authorization, sponsorship, identity, password, OTP, or demographic data.
- Treat CAPTCHA, MFA/OTP, login, payment, and identity-verification gates as blockers unless the user legitimately completes them.
- A browser-agent statement such as `filled` or `saved` is not proof of a successful form change.
- A run is `completed` only when an explicit verification signal is present, such as a verified field value or a verified/visible upload attachment.
- A planned resume/file upload that is not verified is a blocker; JobPilot must not report the run as completed while that upload remains unverified.
- Submission language is a failure/manual-review signal, never a successful application result.
- Agent result text is sanitized before it is returned in an application report to reduce accidental persistence of email addresses, phone numbers, passwords, and verification codes.
- Resume paths are explicitly passed to Browser Use as authorized local upload paths; the path must exist on the machine running JobPilot.
- Browser-agent judging is disabled by default for JobPilot runs to avoid a second model call becoming an unnecessary availability failure after the main run completes.
- An optional OpenAI fallback can be enabled for transient primary-model failures by setting `OPENAI_API_KEY` and `JOBPILOT_FALLBACK_MODEL` in the runtime environment. The fallback is never enabled merely by guessing or inventing credentials.
- 9Router is supported as an OpenAI-compatible primary gateway. When `NINEROUTER_API_KEY` is set, JobPilot uses `ChatOpenAI` against `NINEROUTER_BASE_URL` (default `http://localhost:20128/v1`) and `NINEROUTER_MODEL` (defaulting to the configured JobPilot model). The API key is read only from the runtime environment and must never be committed to source control.
- 9Router's documented setup is to install the router, connect provider credentials in its dashboard, and point compatible tools at `http://localhost:20128/v1`; its routing layer can switch among configured providers. url9Router documentationhttps://docs.9router.com/
- Recommended PowerShell setup after installing/running 9Router locally:
  ```powershell
  $env:NINEROUTER_API_KEY = "YOUR_9ROUTER_KEY"
  $env:NINEROUTER_BASE_URL = "http://localhost:20128/v1"
  $env:NINEROUTER_MODEL = "YOUR_ROUTER_MODEL"
  ```
- Real authenticated browser acceptance testing must use a user-authorized browser profile or a dedicated test account. Production credentials must never be committed to the repository or passed through source-controlled configuration.
