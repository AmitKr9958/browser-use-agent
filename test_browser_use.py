from dotenv import load_dotenv
from browser_use import Agent, BrowserSession, ChatGoogle
from browser_harness.daemon import get_ws_url

load_dotenv()

# Dynamically connect to the Chrome instance managed by Browser Harness.
cdp_url = get_ws_url()

print(f"Connecting to Browser Harness Chrome: {cdp_url.split('/devtools/')[0]}")

browser_session = BrowserSession(
    cdp_url=cdp_url,
)

agent = Agent(
    task="Read the title of the currently active browser tab and tell me the title.",
    llm=ChatGoogle(model="gemini-3.6-flash"),
    browser_session=browser_session,
)

agent.run_sync()
