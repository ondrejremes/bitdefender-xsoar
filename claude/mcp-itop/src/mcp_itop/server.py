"""MCP server pro iTOP ITSM."""
import asyncio
import json
import os
import sys

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from mcp_itop.itop_client import ITOPError
from mcp_itop.tools.customers import list_customers
from mcp_itop.tools.contracts import list_contracts
from mcp_itop.tools.tickets import list_open_tickets, list_open_workorders, search_tickets
from mcp_itop.tools.worklogs import get_worklogs, get_my_worklogs_today, log_work

app = Server("mcp-itop")


@app.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="list_customers",
            description="Vrátí seznam všech zákazníků (Organizations) v iTOP.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="list_contracts",
            description="Vrátí seznam kontraktů (CustomerContracts), volitelně filtrovaných podle zákazníka.",
            inputSchema={
                "type": "object",
                "properties": {
                    "customer_name": {
                        "type": "string",
                        "description": "Část názvu zákazníka pro filtrování (volitelné).",
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="list_open_tickets",
            description="Vrátí otevřené tickety (UserRequests), volitelně filtrované podle zákazníka.",
            inputSchema={
                "type": "object",
                "properties": {
                    "customer_name": {
                        "type": "string",
                        "description": "Část názvu zákazníka pro filtrování (volitelné).",
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="list_open_workorders",
            description="Vrátí otevřené WorkOrders. Lze filtrovat podle čísla ticketu (např. R-000123) nebo zákazníka.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticket_ref": {
                        "type": "string",
                        "description": "Číslo ticketu (ref), např. R-000123 (volitelné).",
                    },
                    "customer_name": {
                        "type": "string",
                        "description": "Část názvu zákazníka pro filtrování (volitelné).",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="search_tickets",
            description="Hledá tickety podle čísla (ref) nebo názvu.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Hledaný text – číslo ticketu nebo část názvu.",
                    }
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_worklogs",
            description=(
                "Vrátí výkazy práce (WorkLogy) za zadané období. "
                "Výchozí rozsah: aktuální měsíc. "
                "Lze filtrovat podle technika nebo zákazníka."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "date_from": {
                        "type": "string",
                        "description": "Datum od ve formátu YYYY-MM-DD (volitelné, výchozí: 1. den měsíce).",
                    },
                    "date_to": {
                        "type": "string",
                        "description": "Datum do ve formátu YYYY-MM-DD (volitelné, výchozí: dnes).",
                    },
                    "technician": {
                        "type": "string",
                        "description": "Část jména technika pro filtrování (volitelné).",
                    },
                    "customer_name": {
                        "type": "string",
                        "description": "Část názvu zákazníka pro filtrování (volitelné).",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="get_my_worklogs_today",
            description="Vrátí dnešní výkazy práce konkrétního technika.",
            inputSchema={
                "type": "object",
                "properties": {
                    "technician": {
                        "type": "string",
                        "description": "Část jména technika (povinné).",
                    }
                },
                "required": ["technician"],
            },
        ),
        Tool(
            name="log_work",
            description=(
                "Vytvoří nový výkaz práce (WorkLog) na zadaný WorkOrder. "
                "Před voláním tohoto nástroje si přes list_open_workorders ověř správné ID WorkOrdu."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "workorder_id": {
                        "type": "integer",
                        "description": "ID WorkOrdu (číslo z iTOP).",
                    },
                    "duration_minutes": {
                        "type": "integer",
                        "description": "Doba trvání práce v minutách.",
                    },
                    "description": {
                        "type": "string",
                        "description": "Popis vykonané práce.",
                    },
                    "log_date": {
                        "type": "string",
                        "description": "Datum výkazu ve formátu YYYY-MM-DD (volitelné, výchozí: dnes).",
                    },
                },
                "required": ["workorder_id", "duration_minutes", "description"],
            },
        ),
    ]


@app.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "list_customers":
            result = await list_customers()

        elif name == "list_contracts":
            result = await list_contracts(
                customer_name=arguments.get("customer_name"),
            )

        elif name == "list_open_tickets":
            result = await list_open_tickets(
                customer_name=arguments.get("customer_name"),
            )

        elif name == "list_open_workorders":
            result = await list_open_workorders(
                ticket_ref=arguments.get("ticket_ref"),
                customer_name=arguments.get("customer_name"),
            )

        elif name == "search_tickets":
            result = await search_tickets(query=arguments["query"])

        elif name == "get_worklogs":
            result = await get_worklogs(
                date_from=arguments.get("date_from"),
                date_to=arguments.get("date_to"),
                technician=arguments.get("technician"),
                customer_name=arguments.get("customer_name"),
            )

        elif name == "get_my_worklogs_today":
            result = await get_my_worklogs_today(technician=arguments["technician"])

        elif name == "log_work":
            result = await log_work(
                workorder_id=arguments["workorder_id"],
                duration_minutes=arguments["duration_minutes"],
                description=arguments["description"],
                log_date=arguments.get("log_date"),
            )

        else:
            return [TextContent(type="text", text=f"Neznámý nástroj: {name}")]

    except ITOPError as e:
        return [TextContent(type="text", text=f"Chyba iTOP: {e}")]
    except KeyError as e:
        return [TextContent(type="text", text=f"Chybí povinný parametr: {e}")]

    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


def main():
    mode = os.getenv("MCP_TRANSPORT", "stdio")
    if mode == "sse":
        _run_sse()
    else:
        asyncio.run(stdio_server(app))


def _run_sse():
    import uvicorn
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Mount, Route

    sse = SseServerTransport("/messages/")

    async def handle_sse(request):
        async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
            await app.run(streams[0], streams[1], app.create_initialization_options())
        from starlette.responses import Response
        return Response()

    starlette_app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse, methods=["GET"]),
            Mount("/messages/", app=sse.handle_post_message),
        ]
    )

    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8000"))
    uvicorn.run(starlette_app, host=host, port=port)


if __name__ == "__main__":
    main()
