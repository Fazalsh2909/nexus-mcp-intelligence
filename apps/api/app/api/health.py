from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "healthy", "service": "nexus-api"}


@router.get("/ready")
async def ready():
    return {"status": "ready"}


@router.get("/metrics")
async def metrics():
    return {
        "status": "ok",
        "service": "nexus-api",
        "version": "1.0.0",
    }
