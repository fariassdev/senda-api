from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.senda.api.routers import course, lesson, auth

# Load environment variables from .env file
load_dotenv()

app = FastAPI(
    title="Senda CMS API",
    description="API for managing and generating guided meditation courses and lessons for the Senda CMS.",
    version="1.0.0",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Set up rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Set up CORS
origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


app.include_router(auth.router, prefix="/api")
app.include_router(course.router, prefix="/api")
app.include_router(lesson.router, prefix="/api")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
