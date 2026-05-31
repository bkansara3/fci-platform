from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, SessionLocal
from app.models import Base
from app.routers import failures, analytics, insights, auth
from app.seeder import seed_failures

# 1. Create database tables
Base.metadata.create_all(bind=engine)


# 2. Define the lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic: Ensure database is ready and seeded
    db = SessionLocal()
    try:
        n = seed_failures(db, count=250)
        if n:
            print(f"[FCI] Seeded {n} mock failures")
        else:
            print("[FCI] Database already seeded")
    finally:
        db.close()
        
    # Yield control back to FastAPI so it can start serving requests
    yield  

    # Shutdown logic would go here (none needed for now)


# 3. Initialize FastAPI and attach the lifespan
app = FastAPI(
    title="FCI Platform",
    version="1.0.0",
    lifespan=lifespan
)

# 4. Add Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 5. Include Routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(failures.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(insights.router, prefix="/api/v1")


# 6. Base Routes
@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)