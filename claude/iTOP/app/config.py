import os
from dotenv import load_dotenv

load_dotenv()

ITOP_URL = os.getenv("ITOP_URL", "")
ITOP_AUTH_TOKEN = os.getenv("ITOP_AUTH_TOKEN", "")

JIRA_URL = os.getenv("JIRA_URL", "")
JIRA_EMAIL = os.getenv("JIRA_EMAIL", "")
JIRA_TOKEN = os.getenv("JIRA_TOKEN", "")
JIRA_PROJECTS = [p.strip() for p in os.getenv("JIRA_PROJECTS", "").split(",") if p.strip()]
