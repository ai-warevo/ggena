from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/health")

@router.get("/live")
async def health_live():
    """Liveness probe: returns 200 if the server is running."""
    return {"status": "ok"}

@router.get("/ready")
async def health_ready(request: Request):
    """Readiness probe: ensures models are loaded before serving traffic."""
    if getattr(request.app.state, "models_loaded", False):
        return {"status": "ready"}
    else:
        raise HTTPException(status_code=503, detail="Models not yet loaded")
