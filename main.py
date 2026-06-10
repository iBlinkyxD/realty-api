from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import engine, Base

# Import all models so Base.metadata knows about them before create_all
import models  # noqa: F401

from routes import auth, listings, upgrade_requests, admin, leads


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="I Love DR Realty API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(listings.router)
app.include_router(upgrade_requests.router)
app.include_router(admin.router)
app.include_router(leads.router)


@app.get("/health")
def health():
    return {"status": "ok"}
