import sys

sys.stdout.reconfigure(encoding="utf-8")

from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Flight Monitor", lifespan=lifespan)

from app.routes.route_groups import router as route_groups_router

app.include_router(route_groups_router, prefix="/api/v1")


@app.get("/")
def root():
    return {"status": "ok", "app": "Flight Monitor"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
