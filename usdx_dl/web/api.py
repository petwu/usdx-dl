"""Web API endpoints."""

import asyncio
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from usdx_dl import cli, models, platform_utils, required_tools, usdb
from usdx_dl.web import state

__all__ = ["router"]

router = APIRouter(prefix="/api")


def setup_done() -> bool:
    """Check if the initial setup is done."""
    cfg = models.Config.load()
    tools = required_tools.query_all()
    return cfg.initial_setup_done and not any(tool.download_required for tool in tools)


class PartialServerConfig(BaseModel):
    """Partial server config for API responses."""

    setup_done: bool
    unlocked_settings: bool
    pause_processing: bool
    is_webview: bool

    model_config = models.config


@router.get("/server-config")
async def get_server_config():
    """Get the current server config."""
    return PartialServerConfig(
        setup_done=setup_done(),
        unlocked_settings=state.server_cfg.unlocked_settings,
        pause_processing=state.server_cfg.pause_processing,
        is_webview=state.server_cfg.is_webview,
    )


@router.get("/usdb/sessions")
def get_usdb_sessions() -> list[models.USDBSession]:
    """Get a list of automatically detected USDB sessions."""
    return usdb.find_sessions()


class USDBCheckRequest(BaseModel):
    """Request type for the /usdb/check endpoint."""

    cookie: str

    model_config = models.config


@router.post("/usdb/check")
def post_usdb_check(req: USDBCheckRequest) -> models.USDBSession | None:
    """Check if a USDB cookie is valid."""
    return usdb.check(req.cookie)


@router.get("/songs")
async def get_songs() -> list[cli.list.ExtendedSongMetadata]:
    """Get a list of all songs."""
    cfg = models.Config.load()
    return cli.list.find_songs(
        output_dir=cfg.output_dir,
        sort_by="artist",
        reverse=False,
    )


@router.get("/songs/folder")
async def get_songs_directory() -> str:
    """Get the path to the output directory."""
    cfg = models.Config.load()
    return str(cfg.output_dir)


class SongsFolderCheckRequest(BaseModel):
    """Request type for the /songs/folder/check endpoint."""

    path: Path

    model_config = models.config


@router.post("/songs/folder/check")
def post_songs_directory_check(req: SongsFolderCheckRequest):
    """Check if a given path is a valid and writable directory."""
    # find first existing parent directory, if that is writable we can create the
    # missing subdirectories
    path = req.path
    while not path.exists() and path.parent != path:
        path = path.parent
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Directory not found: {path}")
    if not path.is_dir():
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {path}")
    if not os.access(path, os.W_OK):
        raise HTTPException(
            status_code=403, detail=f"No write permission for directory: {path}"
        )


class SongsFolderRequest(BaseModel):
    """Request type for the /songs/folder endpoint."""

    id: str | None = None

    model_config = models.config


@router.post("/songs/folder")
async def post_songs_directory_open(req: SongsFolderRequest | None = None) -> None:
    """Open the output directory or a specific song directory in the file explorer."""
    cfg = models.Config.load()
    path = cfg.output_dir / str(req.id) if req and req.id else cfg.output_dir
    if not path.exists():
        raise HTTPException(status_code=404, detail="Directory not found.")
    platform_utils.open_with_default_app(path)


class SongsPatchPatchRequest(BaseModel):
    """Request type for the /songs/folder endpoint."""

    path: Path | None = None
    move: bool = False

    model_config = models.config


@router.patch("/songs/folder")
async def patch_songs_directory(req: SongsPatchPatchRequest) -> Path:
    """Open a file dialog to select a new output directory."""
    cfg = models.Config.load()
    old_dir = cfg.output_dir
    new_dir = req.path or platform_utils.file_dialog(
        title="Select Output Directory",
        filters=["All Files (*)"],
        default=str(cfg.output_dir.parent),
        directory=True,
    )
    if not new_dir or new_dir == old_dir:
        return old_dir

    cfg.output_dir = new_dir
    cfg.save()

    if req.move:
        if not new_dir.exists():
            # target directory doesn't exist, so we can just rename it
            old_dir.rename(new_dir)
        elif not any(new_dir.iterdir()):
            # target directory exists but is empty, so we can remove it and
            # rename the old directory
            new_dir.rmdir()
            old_dir.rename(new_dir)
        elif set(p.name for p in old_dir.iterdir()).isdisjoint(
            set(p.name for p in new_dir.iterdir())
        ):
            # target directory exists and is not empty, but there are no
            # conflicting file/directory names, so we can move the subdirectories
            for p in old_dir.iterdir():
                p.rename(new_dir / p.name)
            old_dir.rmdir()
        else:
            # moving would probably require removing/overwriting files
            raise HTTPException(
                status_code=400,
                detail="Cannot move output directory because the target directory "
                "already exists and contains conflicting files.",
            )

    return cfg.output_dir


@router.get("/tools")
async def get_tools() -> list[models.Tool]:
    """Get a list of all available tools."""
    return required_tools.query_all()


class ToolsDownloadRequest(BaseModel):
    """Request type for the /tools/download endpoint."""

    name: str

    model_config = models.config


@router.post("/tools/download")
async def get_tools_download(req: ToolsDownloadRequest) -> None:
    """Download missing tools."""
    try:
        await asyncio.get_running_loop().run_in_executor(
            None, required_tools.download, req.name
        )
    except Exception as e:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/setup/complete")
async def post_setup_complete() -> None:
    """Mark the setup as complete."""
    cfg = models.Config.load()
    cfg.initial_setup_done = True
    cfg.save()


@router.get("/state")
async def get_state() -> state.ServerState:
    """Get the current server state."""
    return state.processing_state


@router.get("/settings")
async def get_settings() -> models.Config:
    """Get the current server settings."""
    cfg = models.Config.load()
    cfg.pin = None if state.server_cfg.unlocked_settings else "****"
    return cfg


@router.post("/settings")
async def post_settings(cfg: models.Config) -> None:
    """Update the server settings."""
    correct_pin = models.Config.load().pin
    if state.server_cfg.unlocked_settings or not setup_done():
        cfg.pin = correct_pin
    elif correct_pin and cfg.pin != correct_pin:
        raise HTTPException(status_code=403, detail="Invalid PIN.")
    cfg.save()


@router.post("/worker/pause")
async def post_worker_pause() -> None:
    """Pause the processing queue."""
    state.server_cfg.pause_processing = True


@router.post("/worker/resume")
async def post_worker_resume() -> None:
    """Resume the processing queue."""
    state.server_cfg.pause_processing = False


class EnqueueRequest(BaseModel):
    """Request type for the /queue/add endpoint."""

    source: str

    model_config = models.config


@router.post("/queue/add")
async def post_queue_add(req: EnqueueRequest) -> models.PipelineContext:
    """Prepare a download request and add it to the queue."""
    cfg = models.Config.load()
    ctx = models.PipelineContext(
        uuid=cli.download.ctx_uuid(),
        url_or_id=req.source,
        non_interactive=True,
    )
    state.processing_state.pending += 1
    state.processing_state.save()
    try:
        await asyncio.get_running_loop().run_in_executor(
            None, cli.download.prepare, ctx, cfg.output_dir
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=str(e)) from e
    state.processing_state.queue.append(ctx)
    state.processing_state.pending -= 1
    state.processing_state.save()
    return ctx


@router.delete("/queue/remove")
async def delete_queue_remove(ctx: models.PipelineContext):
    """Remove a queued item from the queue."""
    idx = find_ctx(ctx, state.processing_state.queue)
    del state.processing_state.queue[idx]
    state.processing_state.save()


class MoveRequest(BaseModel):
    """Request type for the /queue/move endpoint."""

    item: models.PipelineContext
    direction: str
    to_end: bool

    model_config = models.config


@router.patch("/queue/move")
async def patch_queue_move(req: MoveRequest):
    """Move a queued item up or down in the queue."""
    idx = find_ctx(req.item, state.processing_state.queue)
    if req.direction == "up":
        new_index = 0 if req.to_end else idx - 1
    elif req.direction == "down":
        new_index = len(state.processing_state.queue) - 1 if req.to_end else idx + 1
    else:
        raise HTTPException(status_code=400, detail="Invalid direction.")
    new_index = max(0, min(len(state.processing_state.queue) - 1, new_index))
    state.processing_state.queue.insert(
        new_index, state.processing_state.queue.pop(idx)
    )
    state.processing_state.save()


@router.patch("/queue/update")
async def patch_queue_update(ctx: models.PipelineContext):
    """Update the metadata of a queued item."""
    cfg = models.Config.load()
    ctx.meta = cli.download.update_metadata(ctx, cfg.output_dir)
    idx = find_ctx(ctx, state.processing_state.queue)
    state.processing_state.queue[idx] = ctx
    state.processing_state.save()


@router.patch("/queue/retry")
async def patch_queue_retry(ctx: models.PipelineContext):
    """Retry a failed queued item."""
    idx = find_ctx(ctx, state.processing_state.queue)
    state.processing_state.queue[idx].errors = None
    state.processing_state.save()


def find_ctx(ctx: models.PipelineContext, queue: list[models.PipelineContext]) -> int:
    """Find the index of a context in the queue."""
    for i, item in enumerate(queue):
        if item.uuid == ctx.uuid:
            return i
    raise HTTPException(status_code=404, detail="Item not found in queue.")
