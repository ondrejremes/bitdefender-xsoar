"""Nástroje pro práci s tickety (UserRequests, WorkOrders)."""
from mcp_itop.itop_client import core_get


async def list_open_tickets(customer_name: str | None = None) -> list[dict]:
    """Vrátí otevřené UserRequests a jejich WorkOrders."""
    if customer_name:
        oql = (
            f"SELECT UserRequest AS ur "
            f"JOIN Organization AS o ON ur.org_id = o.id "
            f"WHERE ur.status NOT IN ('closed','resolved') "
            f"AND o.name LIKE '%{customer_name}%'"
        )
    else:
        oql = "SELECT UserRequest WHERE status NOT IN ('closed','resolved')"

    tickets = await core_get(
        "UserRequest",
        oql,
        output_fields="ref,title,status,org_id_friendlyname,agent_id_friendlyname,start_date",
    )
    return sorted(tickets, key=lambda t: t.get("ref", ""))


async def list_open_workorders(ticket_ref: str | None = None, customer_name: str | None = None) -> list[dict]:
    """Vrátí otevřené WorkOrders, volitelně filtrované podle ticketu nebo zákazníka."""
    if ticket_ref:
        oql = (
            f"SELECT WorkOrder AS wo "
            f"JOIN UserRequest AS ur ON wo.ticket_id = ur.id "
            f"WHERE ur.ref = '{ticket_ref}' "
            f"AND wo.status NOT IN ('closed','resolved')"
        )
    elif customer_name:
        oql = (
            f"SELECT WorkOrder AS wo "
            f"JOIN UserRequest AS ur ON wo.ticket_id = ur.id "
            f"JOIN Organization AS o ON ur.org_id = o.id "
            f"WHERE wo.status NOT IN ('closed','resolved') "
            f"AND o.name LIKE '%{customer_name}%'"
        )
    else:
        oql = "SELECT WorkOrder WHERE status NOT IN ('closed','resolved')"

    workorders = await core_get(
        "WorkOrder",
        oql,
        output_fields="name,status,ticket_id_friendlyname,ticket_ref,agent_id_friendlyname,start_date,billing_method",
    )
    return sorted(workorders, key=lambda w: w.get("ticket_id_friendlyname", ""))


async def search_tickets(query: str) -> list[dict]:
    """Fulltext hledání ticketů podle ref nebo názvu."""
    oql = f"SELECT UserRequest WHERE ref LIKE '%{query}%' OR title LIKE '%{query}%'"
    tickets = await core_get(
        "UserRequest",
        oql,
        output_fields="ref,title,status,org_id_friendlyname,agent_id_friendlyname",
        limit=50,
    )
    return tickets
