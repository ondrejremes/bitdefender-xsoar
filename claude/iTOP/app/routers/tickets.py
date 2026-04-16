from collections import defaultdict
from fastapi.templating import Jinja2Templates

from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from app.clients.itop import get_user_requests, get_changes, get_ticket_detail

router = APIRouter(prefix="/tickets", tags=["tickets"])
templates = Jinja2Templates(directory="app/templates")

PRIORITY_LABEL = {"1": "Kritická", "2": "Vysoká", "3": "Střední", "4": "Nízká"}
STATUS_LABEL_UR = {"new": "Nový", "assigned": "Přiřazený", "closed": "Uzavřený"}
STATUS_LABEL_CH = {"new": "Nový", "validated": "Schválený", "assigned": "Přiřazený",
                   "in_progress": "Probíhá", "closed": "Uzavřený", "rejected": "Zamítnutý"}
STATUS_COLOR = {
    "new": "primary", "assigned": "warning", "validated": "info",
    "in_progress": "success", "closed": "secondary", "rejected": "danger",
}
PRIORITY_COLOR = {"1": "danger", "2": "warning", "3": "info", "4": "secondary"}

UR_STATUSES = ["new", "assigned", "closed"]
CH_STATUSES = ["new", "validated", "assigned", "in_progress", "closed", "rejected"]


def _enrich(tickets: list[dict], status_labels: dict) -> list[dict]:
    for t in tickets:
        t["status_label"] = status_labels.get(t["status"], t["status"])
        t["status_color"] = STATUS_COLOR.get(t["status"], "secondary")
        t["priority_label"] = PRIORITY_LABEL.get(t["priority"], "—")
        t["priority_color"] = PRIORITY_COLOR.get(t["priority"], "secondary")
        t["is_general_task"] = t.get("origin", "") == "monitoring"
    return tickets


def _group_by_org(tickets: list[dict]) -> list[tuple]:
    grouped: dict[str, list] = defaultdict(list)
    for t in sorted(tickets, key=lambda x: (x["org"], x["ref"])):
        grouped[t["org"]].append(t)
    return sorted(grouped.items(), key=lambda x: len(x[1]), reverse=True)


@router.get("/", response_class=HTMLResponse)
async def ticket_overview(
    request: Request,
    tab: str = Query(default="userrequests"),
    status: list[str] = Query(default=["new", "assigned"]),
    org_filter: str = Query(default=""),
    show_general: str = Query(default="0"),
):
    if tab == "changes":
        raw = get_changes()
        tickets = _enrich(raw, STATUS_LABEL_CH)
        all_statuses = CH_STATUSES
        status_labels = STATUS_LABEL_CH
    else:
        raw = get_user_requests(status_filter=status if status else None)
        tickets = _enrich(raw, STATUS_LABEL_UR)
        all_statuses = UR_STATUSES
        status_labels = STATUS_LABEL_UR

    # Collect orgs before filtering
    orgs = sorted({t["org"] for t in tickets if t["org"]})

    # Count general tasks before filtering
    general_task_count = sum(1 for t in tickets if t["is_general_task"])
    real_ticket_count = len(tickets) - general_task_count

    # Apply filters
    if org_filter:
        tickets = [t for t in tickets if t["org"] == org_filter]
    if show_general != "1":
        tickets = [t for t in tickets if not t["is_general_task"]]

    grouped = _group_by_org(tickets)

    return templates.TemplateResponse("tickets/index.html", {
        "request": request,
        "tab": tab,
        "grouped": grouped,
        "orgs": orgs,
        "org_filter": org_filter,
        "selected_statuses": status,
        "all_statuses": all_statuses,
        "status_labels": status_labels,
        "status_color": STATUS_COLOR,
        "show_general": show_general,
        "general_task_count": general_task_count,
        "real_ticket_count": real_ticket_count,
        "total": len(tickets),
    })


@router.get("/detail/{ticket_id}", response_class=HTMLResponse)
async def ticket_detail(request: Request, ticket_id: str):
    ticket = get_ticket_detail(ticket_id)
    if not ticket:
        return HTMLResponse("<p class='text-danger'>Ticket nenalezen.</p>", status_code=404)
    return templates.TemplateResponse("tickets/detail.html", {
        "request": request,
        "ticket": ticket,
    })
