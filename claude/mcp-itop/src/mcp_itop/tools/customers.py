"""Nástroje pro práci se zákazníky (Organizations)."""
from mcp_itop.itop_client import core_get


async def list_customers() -> list[dict]:
    """Vrátí seznam všech zákazníků (Organizations)."""
    orgs = await core_get(
        "Organization",
        "SELECT Organization",
        output_fields="name,status,code",
    )
    return sorted(orgs, key=lambda o: o.get("name", ""))
