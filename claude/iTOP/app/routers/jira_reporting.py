import calendar
from datetime import date
from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from fastapi.responses import JSONResponse
from app.clients.jira import get_projects, get_organizations, get_issues_with_worklogs, _post, _get

router = APIRouter(prefix="/reporting/jira", tags=["jira-reporting"])
templates = Jinja2Templates(directory="app/templates")


def _period_dates(period_type: str, year: int, month: int = 1, quarter: int = 1):
    if period_type == "monthly":
        last_day = calendar.monthrange(year, month)[1]
        return date(year, month, 1).isoformat(), date(year, month, last_day).isoformat()
    elif period_type == "quarterly":
        start_month = (quarter - 1) * 3 + 1
        end_month = start_month + 2
        last_day = calendar.monthrange(year, end_month)[1]
        return date(year, start_month, 1).isoformat(), date(year, end_month, last_day).isoformat()
    else:  # yearly
        return date(year, 1, 1).isoformat(), date(year, 12, 31).isoformat()


@router.get("/debug")
async def jira_debug(project_key: str = Query(default="NPSD")):
    """Raw JIRA API debug."""
    result = {}

    # 1. Check auth
    try:
        result["myself"] = _get("/myself", base="/rest/api/3")
    except Exception as e:
        result["myself_error"] = str(e)

    # 2. Check project access
    try:
        result["project"] = _get(f"/project/{project_key}", base="/rest/api/3")
    except Exception as e:
        result["project_error"] = str(e)

    # 3. Fetch known ticket directly
    try:
        result["ticket_NPSD156"] = _get("/issue/NPSD-156", base="/rest/api/3")
    except Exception as e:
        result["ticket_NPSD156_error"] = str(e)

    # 4. Search without fields restriction
    try:
        jql = f'project = "{project_key}" ORDER BY created DESC'
        search = _post("/search/jql", {"jql": jql, "maxResults": 3}, base="/rest/api/3")
        result["search"] = search
    except Exception as e:
        result["search_error"] = str(e)

    return JSONResponse(result)


@router.get("/", response_class=HTMLResponse)
async def jira_report(
    request: Request,
    project_key: str = Query(default=""),
    organization: str = Query(default=""),
    period_type: str = Query(default="monthly"),
    year: int = Query(default=date.today().year),
    month: int = Query(default=date.today().month),
    quarter: int = Query(default=(date.today().month - 1) // 3 + 1),
):
    projects = get_projects()
    organizations = get_organizations(project_key) if project_key else []
    issues = []
    date_from = date_to = ""
    error = None

    if project_key:
        date_from, date_to = _period_dates(period_type, year, month, quarter)
        try:
            issues = get_issues_with_worklogs(project_key, date_from, date_to, organization)
        except Exception as e:
            error = str(e)

    total_h = round(sum(i["period_h"] for i in issues), 2)
    by_assignee: dict[str, float] = {}
    for issue in issues:
        for wl in issue["worklogs"]:
            by_assignee[wl["author"]] = round(by_assignee.get(wl["author"], 0) + wl["duration_h"], 2)

    return templates.TemplateResponse("reporting/jira.html", {
        "request": request,
        "projects": projects,
        "project_key": project_key,
        "organizations": organizations,
        "organization": organization,
        "period_type": period_type,
        "year": year,
        "month": month,
        "quarter": quarter,
        "date_from": date_from,
        "date_to": date_to,
        "issues": issues,
        "total_h": total_h,
        "by_assignee": dict(sorted(by_assignee.items(), key=lambda x: -x[1])),
        "error": error,
        "years": list(range(date.today().year - 2, date.today().year + 1)),
    })
