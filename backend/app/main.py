from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, SessionLocal
from app.models import Base
from app.routers import failures, analytics, insights
from app.seeder import seed_failures
from app.simulator.simulator import start_simulator_thread

# 1. Create database tables
Base.metadata.create_all(bind=engine)


# 2. Define the lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    db = SessionLocal()
    try:
        n = seed_failures(db, count=250)
        if n:
            print(f"[FCI] Seeded {n} mock failures")
        else:
            print("[FCI] Database already seeded")
    finally:
        db.close()
        
    # Start simulator — sends 1 new failure every 10 seconds
    start_simulator_thread(interval_seconds=100)
    print("[FCI] Simulator started — live failures incoming")
    yield  # Hand control back to FastAPI

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