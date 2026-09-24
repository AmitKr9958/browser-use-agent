# LinkedIn Agent

LinkedIn automation layer for the Browser Use project. It reuses an existing Chrome profile so the user's LinkedIn session can be used without storing LinkedIn credentials in the project.

## Capabilities

- Check LinkedIn login/session state
- Search jobs, people, companies and posts
- Inspect profiles and job details
- Draft personalized connection notes and messages
- Publish posts and interact with posts
- Maintain an activity ledger for every planned/executed action
- Support approval gates for high-impact actions
- Run scheduled workflows from the same agent entry point

## Safety defaults

The default mode is `review`. Search, extraction and drafting can run automatically; connection requests, messages, comments, likes and publishing require confirmation unless explicitly enabled in configuration.

The agent does not attempt to bypass CAPTCHAs, LinkedIn security controls, rate limits or account restrictions.

## Setup

1. Install the repository dependencies with the normal Browser Use setup.
2. Ensure Chrome is installed and you have an existing Chrome profile signed into LinkedIn.
3. Copy `config.example.yaml` to `config.yaml` and select the Chrome profile.
4. Set the model/provider using the existing Browser Use environment configuration.
5. Run:

```bash
python -m linkedin_agent.agent --config linkedin_agent/config.yaml --task login-check
```

For an interactive session:

```python
python -m linkedin_agent.agent --config linkedin_agent/config.yaml --task daily-run
```

## Modes

- `review`: research + draft; ask before external actions
- `assisted`: execute low-risk actions; confirm outbound communication
- `full`: execute configured actions automatically, subject to the configured daily caps

Use `review` while validating selectors and workflows. Do not treat `full` as a way to evade LinkedIn enforcement.

## Suggested first workflows

- `login-check`
- `job-search`
- `recruiter-research`
- `content-draft`
- `daily-run`

The initial implementation intentionally keeps the task layer model-driven so LinkedIn UI changes do not require hard-coded selectors for every workflow.
