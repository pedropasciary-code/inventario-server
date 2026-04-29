from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .config import SECRET_KEY, SESSION_COOKIE_SECURE
from .routers import auth, checkin, dashboard, exports
from .routers import audit as audit_router
from .routers import users as users_router

app = FastAPI(title="Inventário Server")
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="inventario_session",
    max_age=8 * 60 * 60,
    same_site="lax",
    https_only=SESSION_COOKIE_SECURE,
)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(users_router.router)
app.include_router(audit_router.router)
app.include_router(exports.router)
app.include_router(checkin.router)


@app.get("/")
def home():
    return {"status": "ok"}
