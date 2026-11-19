import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.routers import (
    auth,
    customers,
    demo,
    enquiries,
    follow_ups,
    knowledge,
    tasks,
    usage,
    users,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(title="Business Ops API")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(customers.router)
app.include_router(enquiries.router)
app.include_router(tasks.router)
app.include_router(knowledge.router)
app.include_router(follow_ups.router)
app.include_router(usage.router)
app.include_router(demo.router)

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


@app.middleware("http")
async def always_check_for_fresh_web_files(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/app"):
        # The browser may keep a copy, but must ask if it is still current.
        response.headers["Cache-Control"] = "no-cache"
    return response


@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse(url="/app/")


@app.get("/health")
def health():
    return {"message": "Business Ops API is running"}


app.mount("/app", StaticFiles(directory=WEB_DIR, html=True), name="web")


# End of file.