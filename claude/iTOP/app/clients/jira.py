import requests
from app.config import JIRA_URL, JIRA_PROJECTS

def _get_session() -> requests.Session:
    from app.config import JIRA_EMAIL, JIRA_TOKEN
    s = requests.Session()
    s.auth = (JIRA_EMAIL, JIRA_TOKEN)
    s.headers.update({"Accept": "application/json"})
    return s


def _raise(resp: requests.Response):
    try:
        body = resp.json()
        msg = body.get("message") or body.get("errorMessages") or str(body)
    except Exception:
        msg = resp.text[:500]
    raise requests.HTTPError(
        f"{resp.status_code} {resp.reason} — {msg}", response=resp
    )


def _get(path: str, params: dict = None, base: str = "/rest/api/2") -> dict:
    resp = _get_session().get(f"{JIRA_URL}{base}{path}", params=params, timeout=30)
    if not resp.ok:
        _raise(resp)
    return resp.json()


def _post(path: str, payload: dict, base: str = "/rest/api/2") -> dict:
    resp = _get_session().post(
        f"{JIRA_URL}{base}{path}",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    if not resp.ok:
        _raise(resp)
    return resp.json()


def get_projects() -> list[dict]:
    """Return configured JIRA projects with display name."""
    result = []
    for key in JIRA_PROJECTS:
        try:
            data = _get(f"/project/{key}")
            result.append({"key": data["key"], "name": data["name"]})
        except Exception:
            result.append({"key": key, "name": key})
    return result


def get_organizations(project_key: str) -> list[dict]:
    """Return organizations for a JSM project via Service Desk API."""
    try:
        # Find service desk ID for this project
        desks = _get("/servicedesk", base="/rest/servicedeskapi")
        desk_id = None
        for desk in desks.get("values", []):
            if desk.get("projectKey") == project_key:
                desk_id = desk["id"]
                break
        if desk_id is None:
            return []
        orgs = _get(f"/servicedesk/{desk_id}/organization", base="/rest/servicedeskapi")
        return [{"id": o["id"], "name": o["name"]} for o in orgs.get("values", [])]
    except Exception:
        return []


def get_issues_with_worklogs(
    project_key: str, date_from: str, date_to: str, organization: str = ""
) -> list[dict]:
    """
    Fetch issues in project that have worklogs within date_from..date_to.
    Optionally filter by organization name.
    date_from / date_to: 'YYYY-MM-DD'
    """
    jql = (
        f'project = "{project_key}" AND worklogDate >= "{date_from}" '
        f'AND worklogDate <= "{date_to}"'
    )
    if organization:
        jql += f' AND organization = "{organization}"'
    jql += " ORDER BY created DESC"

    page_size = 100
    all_issues = []
    next_page_token = None

    while True:
        payload = {
            "jql": jql,
            "maxResults": page_size,
            "fields": ["summary", "status", "assignee", "reporter", "priority", "created",
                       "resolutiondate", "issuetype", "timespent", "timeoriginalestimate"],
        }
        if next_page_token:
            payload["nextPageToken"] = next_page_token

        data = _post("/search/jql", payload, base="/rest/api/3")
        issues = data.get("issues", [])
        all_issues.extend(issues)
        next_page_token = data.get("nextPageToken")
        if not next_page_token or not issues:
            break

    result = []
    for issue in all_issues:
        f = issue["fields"]
        worklogs = _get_worklogs_in_range(issue["key"], date_from, date_to)
        if not worklogs:
            continue
        result.append({
            "key": issue["key"],
            "summary": f.get("summary", ""),
            "status": f.get("status", {}).get("name", ""),
            "assignee": (f.get("assignee") or {}).get("displayName", "Nepřiřazeno"),
            "reporter": (f.get("reporter") or {}).get("displayName", ""),
            "priority": (f.get("priority") or {}).get("name", ""),
            "issue_type": (f.get("issuetype") or {}).get("name", ""),
            "created": (f.get("created") or "")[:10],
            "resolved": (f.get("resolutiondate") or "")[:10],
            "time_spent_h": round((f.get("timespent") or 0) / 3600, 2),
            "url": f"{JIRA_URL}/browse/{issue['key']}",
            "worklogs": worklogs,
            "period_h": round(sum(wl["duration_h"] for wl in worklogs), 2),
        })
    return result


def _get_worklogs_in_range(issue_key: str, date_from: str, date_to: str) -> list[dict]:
    """Fetch worklogs for one issue filtered to the date range."""
    try:
        data = _get(f"/issue/{issue_key}/worklog")
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code in (403, 404):
            return []
        raise
    result = []
    for wl in data.get("worklogs", []):
        started = (wl.get("started") or "")[:10]
        if started < date_from or started > date_to:
            continue
        result.append({
            "author": (wl.get("author") or {}).get("displayName", ""),
            "started": started,
            "duration_h": round((wl.get("timeSpentSeconds") or 0) / 3600, 2),
            "comment": _extract_comment(wl.get("comment")),
        })
    return result


def _extract_comment(comment_doc) -> str:
    """Extract plain text from Atlassian Document Format comment."""
    if not comment_doc or not isinstance(comment_doc, dict):
        return ""
    texts = []
    for block in comment_doc.get("content", []):
        for inline in block.get("content", []):
            if inline.get("type") == "text":
                texts.append(inline.get("text", ""))
    return " ".join(texts).strip()
