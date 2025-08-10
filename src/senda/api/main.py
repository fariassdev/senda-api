from fastapi import FastAPI
from dotenv import load_dotenv
from src.senda.api.routers import course

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


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


app.include_router(course.router, prefix="/api")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
