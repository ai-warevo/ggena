from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()

@router.get("/")
async def read_index():
    """Serves the main frontend page."""
    return FileResponse("src/app/frontend/index.html")
