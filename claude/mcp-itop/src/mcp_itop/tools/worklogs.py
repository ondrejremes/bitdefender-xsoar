"""Nástroje pro vykazování práce (WorkLogs)."""
import os
from datetime import date, datetime
from mcp_itop.itop_client import core_get, core_create


async def get_worklogs(
    date_from: str | None = None,
    date_to: str | None = None,
    technician: str | None = None,
    customer_name: str | None = None,
) -> list[dict]:
    """
    Vrátí WorkLogy za zadané období.

    Parametry:
        date_from: datum od ve formátu YYYY-MM-DD (výchozí: začátek aktuálního měsíce)
        date_to:   datum do ve formátu YYYY-MM-DD (výchozí: dnes)
        technician: část jména technika (volitelné)
        customer_name: část názvu zákazníka (volitelné)
    """
    if not date_from:
        today = date.today()
        date_from = today.replace(day=1).isoformat()
    if not date_to:
        date_to = date.today().isoformat()

    filters = [f"wl.start_date >= '{date_from}'", f"wl.start_date <= '{date_to} 23:59:59'"]

    joins = (
        "SELECT WorkLog AS wl "
        "JOIN WorkOrder AS wo ON wl.workorder_id = wo.id "
        "JOIN UserRequest AS ur ON wo.ticket_id = ur.id "
        "JOIN Organization AS o ON ur.org_id = o.id "
        "JOIN Person AS p ON wl.agent_id = p.id"
    )

    if technician:
        filters.append(f"p.name LIKE '%{technician}%'")
    if customer_name:
        filters.append(f"o.name LIKE '%{customer_name}%'")

    where = " AND ".join(filters)
    oql = f"{joins} WHERE {where}"

    logs = await core_get(
        "WorkLog",
        oql,
        output_fields="start_date,end_date,duration,agent_id_friendlyname,workorder_id_friendlyname,description",
    )

    # Přidáme odvozené pole pro přehlednost
    for log in logs:
        duration_sec = int(log.get("duration") or 0)
        log["duration_hours"] = round(duration_sec / 3600, 2)

    return sorted(logs, key=lambda l: l.get("start_date", ""))


async def get_my_worklogs_today(technician: str) -> list[dict]:
    """Vrátí dnešní výkazy daného technika."""
    today = date.today().isoformat()
    return await get_worklogs(date_from=today, date_to=today, technician=technician)


async def log_work(
    workorder_id: int,
    duration_minutes: int,
    description: str,
    log_date: str | None = None,
    billable: bool | None = None,
) -> dict:
    """
    Vytvoří nový WorkLog na zadaný WorkOrder.

    Parametry:
        workorder_id:      ID WorkOrdu (číslo)
        duration_minutes:  trvání v minutách
        description:       popis vykonané práce
        log_date:          datum výkazu YYYY-MM-DD (výchozí: dnes)
        billable:          True = fakturovatelné, False = nefakturovatelné, None = dle smlouvy
    """
    if not log_date:
        log_date = date.today().isoformat()

    # iTOP ukládá duration v sekundách
    duration_seconds = duration_minutes * 60

    # Načti ticket_id z WorkOrdu
    wo_list = await core_get("WorkOrder", f"SELECT WorkOrder WHERE id = {workorder_id}", "ticket_id,agent_id")
    if not wo_list:
        raise ValueError(f"WorkOrder {workorder_id} nebyl nalezen")
    wo = wo_list[0]

    # agent_id: vezmi z WorkOrdu, nebo fallback na ITOP_DEFAULT_USER
    agent_id = wo.get("agent_id")
    if not agent_id or str(agent_id) == "0":
        default_email = os.getenv("ITOP_DEFAULT_USER", "")
        if default_email:
            persons = await core_get("Person", f"SELECT Person WHERE email = '{default_email}'", "id")
            if persons:
                agent_id = persons[0]["id"]
    if not agent_id:
        raise ValueError("Nepodařilo se určit agenta – nastavte ITOP_DEFAULT_USER v .env")

    fields = {
        "workorder_id": workorder_id,
        "ticket_id": wo["ticket_id"],
        "agent_id": agent_id,
        "description": description,
        "duration": duration_seconds,
        "start_date": f"{log_date} 08:00:00",
    }
    if billable is not None:
        fields["override_billable"] = "yes"
        fields["is_billable"] = "yes" if billable else "no"

    result = await core_create("WorkLog", fields, comment=description)
    result["duration_hours"] = round(duration_seconds / 3600, 2)
    return result
