import io
import calendar
from datetime import date
from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from app.clients.itop import get_contracts, get_contract_report_data
from app.export.external_excel import build_external_excel

router = APIRouter(prefix="/reporting/external", tags=["external-reporting"])
templates = Jinja2Templates(directory="app/templates")

LOGO_PATH = "app/static/logo.png"


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


def _period_label(period_type, year, month, quarter, lang):
    months_cs = ["", "Leden", "Únor", "Březen", "Duben", "Květen", "Červen",
                 "Červenec", "Srpen", "Září", "Říjen", "Listopad", "Prosinec"]
    months_en = ["", "January", "February", "March", "April", "May", "June",
                 "July", "August", "September", "October", "November", "December"]
    months = months_cs if lang == "cs" else months_en
    if period_type == "monthly":
        return f"{months[month]} {year}"
    elif period_type == "quarterly":
        return f"Q{quarter} {year}"
    return str(year)


@router.get("/", response_class=HTMLResponse)
async def external_report(
    request: Request,
    contract_id: str = Query(default=""),
    period_type: str = Query(default="monthly"),
    year: int = Query(default=date.today().year),
    month: int = Query(default=date.today().month),
    quarter: int = Query(default=(date.today().month - 1) // 3 + 1),
    lang: str = Query(default="cs"),
    show_general: str = Query(default="1"),
):
    contracts = get_contracts()
    report_data = None
    date_from = date_to = ""

    if contract_id:
        date_from, date_to = _period_dates(period_type, year, month, quarter)
        raw = get_contract_report_data(contract_id, date_from, date_to)
        contract = raw["contract"]
        tickets = raw["tickets"]

        portal = [t for t in tickets if not t["is_general_task"]]
        gen = [t for t in tickets if t["is_general_task"]]
        all_wl = [wl for t in tickets for wo in t["workorders"] for wl in wo["worklogs"]]

        report_data = {
            "contract": contract,
            "tickets": tickets,
            "portal_tickets": portal,
            "gen_tickets": gen,
            "total_h": round(sum(wl["duration_h"] for wl in all_wl), 2),
            "billable_h": round(sum(wl["duration_h"] for wl in all_wl if wl["is_billable"]), 2),
            "period_label": _period_label(period_type, year, month, quarter, lang),
        }

    return templates.TemplateResponse("reporting/external.html", {
        "request": request,
        "contracts": contracts,
        "contract_id": contract_id,
        "period_type": period_type,
        "year": year,
        "month": month,
        "quarter": quarter,
        "lang": lang,
        "show_general": show_general,
        "date_from": date_from,
        "date_to": date_to,
        "report_data": report_data,
        "years": list(range(date.today().year - 2, date.today().year + 1)),
    })


@router.get("/export/xls")
async def export_xls(
    contract_id: str = Query(default=""),
    period_type: str = Query(default="monthly"),
    year: int = Query(default=date.today().year),
    month: int = Query(default=date.today().month),
    quarter: int = Query(default=1),
    lang: str = Query(default="cs"),
    show_general: str = Query(default="1"),
):
    date_from, date_to = _period_dates(period_type, year, month, quarter)
    raw = get_contract_report_data(contract_id, date_from, date_to)
    label = _period_label(period_type, year, month, quarter, lang)

    content = build_external_excel(
        contract=raw["contract"],
        tickets=raw["tickets"],
        date_from=date_from,
        date_to=date_to,
        lang=lang,
        logo_path=LOGO_PATH,
    )

    org = raw["contract"]["org"].replace(" ", "_")
    contract_name = raw["contract"]["name"].replace(":", "-").replace(" ", "_")
    filename = f"{org}_{contract_name}_{label.replace(' ', '_')}.xlsx"

    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
