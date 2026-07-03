"""Serve static assets from the output directory."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from usdx_dl import models

router = APIRouter()


@router.get("/songs/{rel_path:path}")
async def get_songs_file(rel_path: str):
    """Serve a song file from the output directory."""
    cfg = models.Config.load()
    path = (cfg.output_dir / rel_path).resolve()
    if not path.is_relative_to(cfg.output_dir):
        raise HTTPException(status_code=403)
    if not path.is_file():
        raise HTTPException(status_code=404)
    return FileResponse(path)
