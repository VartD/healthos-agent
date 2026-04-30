from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import Base, engine
from app.routes import events


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="HealthOS Agent", lifespan=lifespan)


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "HealthOS running"}


app.include_router(events.router)
