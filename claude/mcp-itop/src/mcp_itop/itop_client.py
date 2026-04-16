"""iTOP REST API klient."""
import json
import os
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

ITOP_URL = os.getenv("ITOP_URL", "").rstrip("/")
ITOP_AUTH_TOKEN = os.getenv("ITOP_AUTH_TOKEN", "")
REST_ENDPOINT = f"{ITOP_URL}/webservices/rest.php"


class ITOPError(Exception):
    pass


async def _call(operation: str, class_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Zavolá iTOP REST API s danou operací."""
    if not ITOP_URL or not ITOP_AUTH_TOKEN:
        raise ITOPError("ITOP_URL nebo ITOP_AUTH_TOKEN není nastaveno")

    json_data = {"operation": operation, "class": class_name, **payload}

    async with httpx.AsyncClient(verify=False, timeout=60.0) as client:
        response = await client.post(
            REST_ENDPOINT,
            data={
                "version": "1.3",
                "auth_token": ITOP_AUTH_TOKEN,
                "json_data": json.dumps(json_data),
            },
        )
        response.raise_for_status()

    result = response.json()
    if result.get("code") != 0:
        raise ITOPError(f"iTOP chyba {result.get('code')}: {result.get('message')}")

    return result.get("objects") or {}


async def core_get(
    class_name: str,
    oql: str,
    output_fields: str = "*",
    limit: int = 0,
) -> list[dict[str, Any]]:
    """Načte objekty z iTOP pomocí OQL dotazu."""
    payload: dict[str, Any] = {
        "key": oql,
        "output_fields": output_fields,
    }
    if limit > 0:
        payload["limit"] = limit

    objects = await _call("core/get", class_name, payload)
    return [{"id": obj["key"], **obj["fields"]} for obj in objects.values()]


async def core_create(class_name: str, fields: dict[str, Any], comment: str = "") -> dict[str, Any]:
    """Vytvoří nový objekt v iTOP."""
    payload = {"fields": fields, "output_fields": "id", "comment": comment}
    objects = await _call("core/create", class_name, payload)
    if objects:
        first = next(iter(objects.values()))
        return {"id": first["key"], **first["fields"]}
    raise ITOPError("Vytvoření objektu se nezdařilo – prázdná odpověď")


async def core_update(class_name: str, key: str | int, fields: dict[str, Any]) -> dict[str, Any]:
    """Aktualizuje existující objekt v iTOP."""
    payload = {"key": str(key), "fields": fields, "output_fields": "id"}
    objects = await _call("core/update", class_name, payload)
    if objects:
        first = next(iter(objects.values()))
        return {"id": first["key"], **first["fields"]}
    raise ITOPError("Aktualizace objektu se nezdařila – prázdná odpověď")
