from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from config import settings
from database import engine, Base
from utils.limiter import limiter

# Import all models so Base.metadata knows about them before create_all
import models  # noqa: F401

from routes import auth, listings, upgrade_requests, admin, leads, inquiries, saved_homes, bookings


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="I Love DR Realty API", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

app.include_router(auth.router)
app.include_router(listings.router)
app.include_router(upgrade_requests.router)
app.include_router(admin.router)
app.include_router(leads.router)
app.include_router(inquiries.router)
app.include_router(saved_homes.router)
app.include_router(bookings.router)


@app.get("/health")
def health():
    return {"status": "ok"}
