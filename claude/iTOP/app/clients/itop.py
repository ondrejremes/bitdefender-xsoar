import json
import requests
from app.config import ITOP_URL, ITOP_AUTH_TOKEN

requests.packages.urllib3.disable_warnings()


def _call(operation: dict) -> dict:
    response = requests.post(
        f"{ITOP_URL}/webservices/rest.php",
        data={
            "version": "1.3",
            "auth_token": ITOP_AUTH_TOKEN,
            "json_data": json.dumps(operation),
        },
        verify=False,
        timeout=30,
    )
    data = response.json()
    if data.get("code") != 0:
        raise RuntimeError(f"iTop API error: {data.get('message')}")
    return data


def get_worklogs(date_from: str, date_to: str) -> list[dict]:
    """
    Fetch all WorkLogs in a date range and enrich with contract/org from parent ticket.
    date_from / date_to: 'YYYY-MM-DD'
    """
    result = _call({
        "operation": "core/get",
        "class": "WorkLog",
        "key": (
            f"SELECT WorkLog WHERE start_date >= '{date_from} 00:00:00'"
            f" AND start_date <= '{date_to} 23:59:59'"
        ),
        "output_fields": "*",
        "limit": 0,
    })
    worklogs = []
    for item in (result.get("objects") or {}).values():
        f = item["fields"]
        worklogs.append({
            "id": item["key"],
            "agent": f.get("agent_id_friendlyname", ""),
            "agent_id": f.get("agent_id", ""),
            "start_date": f.get("start_date", ""),
            "end_date": f.get("end_date", ""),
            "duration_sec": int(f.get("duration") or 0),
            "duration_h": round(int(f.get("duration") or 0) / 3600, 2),
            "description": f.get("description", ""),
            "is_billable": f.get("is_billable", "no") == "yes",
            "workorder": f.get("workorder_id_friendlyname", ""),
            "ticket_ref": f.get("ticket_id_friendlyname", ""),
            "ticket_id": f.get("ticket_id", ""),
        })
    return worklogs


def get_tickets_by_ids(ticket_ids: list[str]) -> dict[str, dict]:
    """Fetch UserRequests by IDs and return dict keyed by ticket id."""
    if not ticket_ids:
        return {}
    ids_str = ",".join(ticket_ids)
    result = _call({
        "operation": "core/get",
        "class": "UserRequest",
        "key": f"SELECT UserRequest WHERE id IN ({ids_str})",
        "output_fields": "ref,org_name,contract_id,contract_id_friendlyname,org_id_friendlyname",
        "limit": 0,
    })
    tickets = {}
    for item in (result.get("objects") or {}).values():
        f = item["fields"]
        tickets[item["key"]] = {
            "ref": f.get("ref", ""),
            "org": f.get("org_id_friendlyname", f.get("org_name", "")),
            "contract_id": f.get("contract_id", ""),
            "contract": f.get("contract_id_friendlyname", ""),
        }
    return tickets


def get_user_requests(status_filter: list[str] = None) -> list[dict]:
    """Fetch UserRequests, optionally filtered by status list."""
    if status_filter:
        statuses = ", ".join(f"'{s}'" for s in status_filter)
        key = f"SELECT UserRequest WHERE status IN ({statuses})"
    else:
        key = "SELECT UserRequest"

    result = _call({
        "operation": "core/get",
        "class": "UserRequest",
        "key": key,
        "output_fields": (
            "ref,org_name,org_id_friendlyname,caller_id_friendlyname,"
            "agent_id_friendlyname,title,status,priority,start_date,"
            "close_date,contract_id_friendlyname,request_type,last_update,"
            "origin,service_id_friendlyname,servicesubcategory_id_friendlyname"
        ),
        "limit": 0,
    })

    tickets = []
    for item in (result.get("objects") or {}).values():
        f = item["fields"]
        tickets.append({
            "id": item["key"],
            "ref": f.get("ref", ""),
            "org": f.get("org_id_friendlyname") or f.get("org_name", ""),
            "caller": f.get("caller_id_friendlyname", "").strip(),
            "agent": f.get("agent_id_friendlyname", "").strip(),
            "title": f.get("title", ""),
            "status": f.get("status", ""),
            "priority": f.get("priority", ""),
            "request_type": f.get("request_type", ""),
            "start_date": f.get("start_date", ""),
            "close_date": f.get("close_date", ""),
            "last_update": f.get("last_update", ""),
            "contract": f.get("contract_id_friendlyname", ""),
            "origin": f.get("origin", ""),
            "service": f.get("service_id_friendlyname", ""),
            "subcategory": f.get("servicesubcategory_id_friendlyname", ""),
        })
    return tickets


def get_ticket_detail(ticket_id: str) -> dict | None:
    """Fetch single UserRequest with full WorkOrder and WorkLog detail."""
    result = _call({
        "operation": "core/get",
        "class": "UserRequest",
        "key": f"SELECT UserRequest WHERE id = {ticket_id}",
        "output_fields": "*",
        "limit": 1,
    })
    objects = result.get("objects") or {}
    if not objects:
        return None
    item = next(iter(objects.values()))
    f = item["fields"]

    workorders = []
    for wo in f.get("workorders_list", []):
        worklogs = []
        for wl in wo.get("worklogs_list", []):
            worklogs.append({
                "id": wl.get("id", ""),
                "agent": wl.get("agent_id_friendlyname", "").strip(),
                "start_date": wl.get("start_date", ""),
                "end_date": wl.get("end_date", ""),
                "duration_h": round(int(wl.get("duration") or 0) / 3600, 2),
                "description": wl.get("description", ""),
                "is_billable": wl.get("is_billable", "no") == "yes",
            })
        workorders.append({
            "name": wo.get("name", ""),
            "status": wo.get("status", ""),
            "agent": wo.get("agent_id_friendlyname", "").strip(),
            "billing_method": wo.get("billing_method", ""),
            "start_date": wo.get("start_date", ""),
            "end_date": wo.get("end_date", ""),
            "total_h": round(sum(int(wl.get("duration") or 0) for wl in wo.get("worklogs_list", [])) / 3600, 2),
            "worklogs": worklogs,
        })

    return {
        "id": item["key"],
        "ref": f.get("ref", ""),
        "title": f.get("title", ""),
        "org": f.get("org_id_friendlyname") or f.get("org_name", ""),
        "caller": f.get("caller_id_friendlyname", "").strip(),
        "agent": f.get("agent_id_friendlyname", "").strip(),
        "status": f.get("status", ""),
        "priority": f.get("priority", ""),
        "start_date": f.get("start_date", ""),
        "close_date": f.get("close_date", ""),
        "contract": f.get("contract_id_friendlyname", ""),
        "description": f.get("description", ""),
        "origin": f.get("origin", ""),
        "service": f.get("service_id_friendlyname", ""),
        "subcategory": f.get("servicesubcategory_id_friendlyname", ""),
        "tto_h": round(int(f.get("tto") or 0) / 3600, 2) if f.get("tto") else None,
        "ttr_h": round(int(f.get("ttr") or 0) / 3600, 2) if f.get("ttr") else None,
        "sla_tto_passed": f.get("sla_tto_passed", "no") == "yes",
        "sla_ttr_passed": f.get("sla_ttr_passed", "no") == "yes",
        "workorders": workorders,
    }


def get_changes(status_filter: list[str] = None) -> list[dict]:
    """Fetch Changes, optionally filtered by status list."""
    if status_filter:
        statuses = ", ".join(f"'{s}'" for s in status_filter)
        key = f"SELECT Change WHERE status IN ({statuses})"
    else:
        key = "SELECT Change"

    result = _call({
        "operation": "core/get",
        "class": "Change",
        "key": key,
        "output_fields": (
            "ref,org_name,org_id_friendlyname,caller_id_friendlyname,"
            "agent_id_friendlyname,title,status,start_date,close_date,last_update,category"
        ),
        "limit": 0,
    })

    changes = []
    for item in (result.get("objects") or {}).values():
        f = item["fields"]
        changes.append({
            "id": item["key"],
            "ref": f.get("ref", ""),
            "org": f.get("org_id_friendlyname") or f.get("org_name", ""),
            "caller": f.get("caller_id_friendlyname", "").strip(),
            "agent": f.get("agent_id_friendlyname", "").strip(),
            "title": f.get("title", ""),
            "status": f.get("status", ""),
            "priority": "",
            "request_type": "change",
            "category": f.get("category", ""),
            "start_date": f.get("start_date", ""),
            "close_date": f.get("close_date", ""),
            "last_update": f.get("last_update", ""),
            "contract": "",
            "is_general_task": False,
        })
    return changes


def get_contract_report_data(contract_id: str, date_from: str, date_to: str) -> dict:
    """Fetch all data needed for external report: contract info + tickets + worklogs."""
    # Contract detail
    c_result = _call({
        "operation": "core/get",
        "class": "CustomerContract",
        "key": f"SELECT CustomerContract WHERE id = {contract_id}",
        "output_fields": "*",
        "limit": 1,
    })
    contract = {}
    for item in (c_result.get("objects") or {}).values():
        f = item["fields"]
        contract = {
            "id": item["key"],
            "name": f.get("name", ""),
            "org": f.get("org_id_friendlyname", ""),
            "budget_mode": f.get("budget_mode", "none"),
            "monthly_hours_budget": float(f.get("monthly_hours_budget") or 0),
            "monthly_budgets": f.get("monthly_budgets_list", []),
        }

    # UserRequests for this contract in the period
    ur_result = _call({
        "operation": "core/get",
        "class": "UserRequest",
        "key": (
            f"SELECT UserRequest WHERE contract_id = {contract_id}"
            f" AND start_date >= '{date_from} 00:00:00'"
            f" AND start_date <= '{date_to} 23:59:59'"
        ),
        "output_fields": "*",
        "limit": 0,
    })

    tickets = []
    for item in (ur_result.get("objects") or {}).values():
        f = item["fields"]
        workorders = []
        for wo in f.get("workorders_list", []):
            worklogs = []
            for wl in wo.get("worklogs_list", []):
                worklogs.append({
                    "id": wl.get("id", ""),
                    "agent": wl.get("agent_id_friendlyname", "").strip(),
                    "start_date": wl.get("start_date", ""),
                    "duration_h": round(int(wl.get("duration") or 0) / 3600, 2),
                    "description": wl.get("description", ""),
                    "is_billable": wl.get("is_billable", "no") == "yes",
                })
            workorders.append({
                "name": wo.get("name", ""),
                "status": wo.get("status", ""),
                "billing_method": wo.get("billing_method", ""),
                "total_h": round(sum(int(wl.get("duration") or 0) for wl in wo.get("worklogs_list", [])) / 3600, 2),
                "worklogs": worklogs,
            })

        tto_sec = int(f.get("tto") or 0)
        ttr_sec = int(f.get("ttr") or 0)
        tickets.append({
            "id": item["key"],
            "ref": f.get("ref", ""),
            "title": f.get("title", ""),
            "caller": f.get("caller_id_friendlyname", "").strip(),
            "agent": f.get("agent_id_friendlyname", "").strip(),
            "status": f.get("status", ""),
            "priority": f.get("priority", ""),
            "origin": f.get("origin", ""),
            "is_general_task": f.get("origin", "") == "monitoring",
            "start_date": f.get("start_date", ""),
            "close_date": f.get("close_date", ""),
            "tto_h": round(tto_sec / 3600, 2) if tto_sec else None,
            "ttr_h": round(ttr_sec / 3600, 2) if ttr_sec else None,
            "sla_tto_passed": f.get("sla_tto_passed", "no") == "yes",
            "sla_ttr_passed": f.get("sla_ttr_passed", "no") == "yes",
            "workorders": workorders,
            "total_h": sum(wo["total_h"] for wo in workorders),
        })

    return {"contract": contract, "tickets": tickets}


def get_contracts() -> list[dict]:
    """Fetch all CustomerContracts."""
    result = _call({
        "operation": "core/get",
        "class": "CustomerContract",
        "key": "SELECT CustomerContract WHERE status = 'production'",
        "output_fields": "name,org_id_friendlyname,budget_mode,monthly_hours_budget",
        "limit": 0,
    })
    contracts = []
    for item in (result.get("objects") or {}).values():
        f = item["fields"]
        contracts.append({
            "id": item["key"],
            "name": f.get("name", ""),
            "org": f.get("org_id_friendlyname", ""),
            "budget_mode": f.get("budget_mode", ""),
            "monthly_hours_budget": float(f.get("monthly_hours_budget") or 0),
        })
    return sorted(contracts, key=lambda c: c["name"])
