from collections import defaultdict
from datetime import date, timedelta
from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
import io

from app.clients.itop import get_worklogs, get_tickets_by_ids, get_contracts
from app.export.excel import build_excel
from app.export.pdf import build_pdf

router = APIRouter(prefix="/reporting", tags=["reporting"])
templates = Jinja2Templates(directory="app/templates")


def _default_period():
    today = date.today()
    first = today.replace(day=1)
    if first.month == 12:
        last = first.replace(day=31)
    else:
        last = first.replace(month=first.month + 1, day=1) - timedelta(days=1)
    return first.isoformat(), last.isoformat()


def _enrich_worklogs(worklogs: list[dict]) -> list[dict]:
    ticket_ids = list({wl["ticket_id"] for wl in worklogs if wl["ticket_id"]})
    tickets = get_tickets_by_ids(ticket_ids)
    for wl in worklogs:
        t = tickets.get(wl["ticket_id"], {})
        wl["org"] = t.get("org", "—")
        wl["contract"] = t.get("contract", "—")
        wl["contract_id"] = t.get("contract_id", "")
    return worklogs


def _filter_by_agent(worklogs: list[dict], agent: str) -> list[dict]:
    if not agent:
        return worklogs
    return [wl for wl in worklogs if wl["agent"] == agent]


def _aggregate_by_agent(worklogs: list[dict]) -> list[dict]:
    data = defaultdict(lambda: {"hours": 0.0, "hours_billable": 0.0, "entries": 0})
    for wl in worklogs:
        key = wl["agent"] or "Neznámý"
        data[key]["hours"] = round(data[key]["hours"] + wl["duration_h"], 2)
        data[key]["entries"] += 1
        if wl["is_billable"]:
            data[key]["hours_billable"] = round(data[key]["hours_billable"] + wl["duration_h"], 2)
    return sorted([{"agent": k, **v} for k, v in data.items()], key=lambda x: x["hours"], reverse=True)


def _aggregate_by_contract(worklogs: list[dict]) -> list[dict]:
    data = defaultdict(lambda: {"org": "", "hours": 0.0, "hours_billable": 0.0, "entries": 0})
    for wl in worklogs:
        key = wl["contract"] or "—"
        data[key]["org"] = wl["org"]
        data[key]["hours"] = round(data[key]["hours"] + wl["duration_h"], 2)
        data[key]["entries"] += 1
        if wl["is_billable"]:
            data[key]["hours_billable"] = round(data[key]["hours_billable"] + wl["duration_h"], 2)
    return sorted([{"contract": k, **v} for k, v in data.items()], key=lambda x: x["hours"], reverse=True)


def _aggregate_by_workorder(worklogs: list[dict]) -> list[dict]:
    data = defaultdict(lambda: {"hours": 0.0, "hours_billable": 0.0, "entries": 0})
    for wl in worklogs:
        key = wl["workorder"] or "—"
        data[key]["hours"] = round(data[key]["hours"] + wl["duration_h"], 2)
        data[key]["entries"] += 1
        if wl["is_billable"]:
            data[key]["hours_billable"] = round(data[key]["hours_billable"] + wl["duration_h"], 2)
    return sorted([{"workorder": k, **v} for k, v in data.items()], key=lambda x: x["hours"], reverse=True)


def _build_report_data(date_from: str, date_to: str, agent_filter: str):
    worklogs = get_worklogs(date_from, date_to)
    worklogs = _enrich_worklogs(worklogs)
    worklogs = _filter_by_agent(worklogs, agent_filter)

    agents = sorted({wl["agent"] for wl in worklogs if wl["agent"]})
    total_h = round(sum(wl["duration_h"] for wl in worklogs), 2)
    total_billable_h = round(sum(wl["duration_h"] for wl in worklogs if wl["is_billable"]), 2)

    return {
        "worklogs": sorted(worklogs, key=lambda x: x["start_date"], reverse=True),
        "agents": agents,
        "total_h": total_h,
        "total_billable_h": total_billable_h,
        "by_agent": _aggregate_by_agent(worklogs),
        "by_contract": _aggregate_by_contract(worklogs),
        "by_workorder": _aggregate_by_workorder(worklogs),
    }


@router.get("/internal", response_class=HTMLResponse)
async def internal_report(
    request: Request,
    date_from: str = Query(default=""),
    date_to: str = Query(default=""),
    agent: str = Query(default=""),
):
    if not date_from or not date_to:
        date_from, date_to = _default_period()

    data = _build_report_data(date_from, date_to, agent)

    return templates.TemplateResponse("reporting/internal.html", {
        "request": request,
        "date_from": date_from,
        "date_to": date_to,
        "agent_filter": agent,
        **data,
    })


@router.get("/internal/export/xls")
async def export_xls(
    date_from: str = Query(default=""),
    date_to: str = Query(default=""),
    agent: str = Query(default=""),
):
    if not date_from or not date_to:
        date_from, date_to = _default_period()

    data = _build_report_data(date_from, date_to, agent)
    export_data = {k: v for k, v in data.items() if k != "agents"}
    content = build_excel(date_from, date_to, **export_data)

    agent_suffix = f"_{agent.replace(' ', '_')}" if agent else ""
    filename = f"report_{date_from}_{date_to}{agent_suffix}.xlsx"

    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/internal/export/pdf")
async def export_pdf(
    date_from: str = Query(default=""),
    date_to: str = Query(default=""),
    agent: str = Query(default=""),
):
    if not date_from or not date_to:
        date_from, date_to = _default_period()

    data = _build_report_data(date_from, date_to, agent)
    export_data = {k: v for k, v in data.items() if k != "agents"}
    content = build_pdf(date_from, date_to, agent_filter=agent, **export_data)

    agent_suffix = f"_{agent.replace(' ', '_')}" if agent else ""
    filename = f"report_{date_from}_{date_to}{agent_suffix}.pdf"

    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
