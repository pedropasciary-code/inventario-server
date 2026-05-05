import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from starlette.middleware.sessions import SessionMiddleware

from .config import CHECKIN_RETENTION_DAYS, SECRET_KEY, SESSION_COOKIE_SECURE, TRUSTED_PROXIES
from .rate_limiting import cleanup_stale_entries
from .services.asset import purge_old_checkins
from .routers import auth, checkin, dashboard, exports
from .routers import audit as audit_router
from .routers import topology as topology_router
from .routers import users as users_router


APP_DIR = Path(__file__).resolve().parent


async def _background_maintenance_task():
    while True:
        await asyncio.sleep(6 * 60 * 60)  # every 6 hours
        cleanup_stale_entries()
        purge_old_checkins(CHECKIN_RETENTION_DAYS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run once at startup, then every 6 hours
    cleanup_stale_entries()
    purge_old_checkins(CHECKIN_RETENTION_DAYS)
    task = asyncio.create_task(_background_maintenance_task())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="Inventário Server", docs_url=None, redoc_url=None, lifespan=lifespan)

if TRUSTED_PROXIES:
    trusted = TRUSTED_PROXIES if TRUSTED_PROXIES == "*" else [ip.strip() for ip in TRUSTED_PROXIES.split(",")]
    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=trusted)

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="inventario_session",
    max_age=8 * 60 * 60,
    same_site="lax",
    https_only=SESSION_COOKIE_SECURE,
)
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(users_router.router)
app.include_router(audit_router.router)
app.include_router(exports.router)
app.include_router(checkin.router)
app.include_router(topology_router.router)


@app.get("/")
def home():
    return {"status": "ok"}
