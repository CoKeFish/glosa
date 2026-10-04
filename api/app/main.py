from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import models  # noqa: F401  (registers tables)
from app.db import Base, engine
from app.routers import assist, books, terms


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # No migrations yet: the schema is still moving. Switch to Alembic before the first real release.
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="glosa", lifespan=lifespan)
app.include_router(books.router)
app.include_router(terms.router)
app.include_router(assist.router)


@app.get("/api/health")
def health():
    return {"ok": True}
