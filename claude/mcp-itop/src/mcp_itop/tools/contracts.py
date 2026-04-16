"""Nástroje pro práci s kontrakty (CustomerContracts)."""
from mcp_itop.itop_client import core_get


async def list_contracts(customer_name: str | None = None) -> list[dict]:
    """Vrátí seznam kontraktů, volitelně filtrovaných podle zákazníka."""
    if customer_name:
        oql = (
            f"SELECT CustomerContract AS cc "
            f"JOIN Organization AS o ON cc.org_id = o.id "
            f"WHERE o.name LIKE '%{customer_name}%'"
        )
    else:
        oql = "SELECT CustomerContract"

    contracts = await core_get(
        "CustomerContract",
        oql,
        output_fields="name,org_id_friendlyname,start_date,end_date,status",
    )
    return sorted(contracts, key=lambda c: c.get("org_id_friendlyname", ""))
