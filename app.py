"""
SimOracle FastAPI backend server
Institutional prediction engine with real-time market analytics
"""
import logging
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime

from config import HOST, PORT, DEBUG
from database.schema import init_database
from api.routes import router as api_router
from api.integration_routes import router as integration_router
from market_feeds.kalshi import get_kalshi_client

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Background tasks
async def startup_tasks():
    """Run on startup"""
    logger.info("Initializing SimOracle backend...")

    # Initialize database
    try:
        init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

    # Initialize Kalshi client
    try:
        kalshi = await get_kalshi_client()
        logger.info("Kalshi client initialized")
    except Exception as e:
        logger.warning(f"Kalshi client initialization warning: {e}")

    logger.info("Startup complete")


async def shutdown_tasks():
    """Run on shutdown"""
    logger.info("Shutting down SimOracle backend...")
    try:
        kalshi = await get_kalshi_client()
        await kalshi.close()
        logger.info("Kalshi client closed")
    except Exception as e:
        logger.warning(f"Kalshi client shutdown warning: {e}")

    logger.info("Shutdown complete")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager"""
    await startup_tasks()
    yield
    await shutdown_tasks()


# Create FastAPI app
app = FastAPI(
    title="SimOracle Backend",
    description="Institutional prediction engine with real-time market analytics",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include API routes
app.include_router(api_router)
app.include_router(integration_router)


# Root endpoint
@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "service": "SimOracle Backend",
        "version": "0.1.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "docs": "/docs",
        "endpoints": {
            "predictions": "/api/v1/predictions",
            "whale_activity": "/api/v1/analytics/whale-activity",
            "arbitrage": "/api/v1/analytics/arbitrage",
            "insider_signals": "/api/v1/analytics/insider-signals",
            "health": "/api/v1/health",
        }
    }


# Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if DEBUG else None,
            "timestamp": datetime.now().isoformat(),
        }
    )


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting SimOracle backend on {HOST}:{PORT}")
    uvicorn.run(
        "app:app",
        host=HOST,
        port=PORT,
        reload=DEBUG,
        log_level="debug" if DEBUG else "info",
    )
