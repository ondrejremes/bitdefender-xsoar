from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from app.routers import reporting, tickets, external_reporting, jira_reporting, agrofert_import

app = FastAPI(title="iTop Portal")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(reporting.router)
app.include_router(external_reporting.router)
app.include_router(jira_reporting.router)
app.include_router(tickets.router)
app.include_router(agrofert_import.router)


@app.get("/")
async def root():
    return RedirectResponse(url="/reporting/internal")
