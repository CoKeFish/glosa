from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app import config, migrate
from app.routers import assist, auth, books, terms


@asynccontextmanager
async def lifespan(_app: FastAPI):
    migrate.upgrade()
    yield


app = FastAPI(title="glosa", lifespan=lifespan)


@app.middleware("http")
async def check_origin(request: Request, call_next):
    """On the hosted service, refuse state-changing requests sent by another site's page.
    The session cookie is SameSite=Lax already; this closes the remaining gaps."""
    if config.hosted() and request.method not in ("GET", "HEAD", "OPTIONS"):
        origin = request.headers.get("origin")
        # Proxies in front (Vite in development, nginx and Traefik in production) may rewrite
        # Host; the public address and the forwarded host are the site's own too.
        own = {request.headers.get("host"), request.headers.get("x-forwarded-host"), urlparse(config.public_url()).netloc}
        if origin and urlparse(origin).netloc not in own:
            return JSONResponse({"detail": "Origen no permitido"}, status_code=403)
    return await call_next(request)


app.include_router(auth.router)
app.include_router(books.router)
app.include_router(terms.router)
app.include_router(assist.router)


@app.get("/api/health")
def health():
    return {"ok": True}
