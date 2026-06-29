"""Web API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from usdx_dl import cli, config, interactive, models, platform_utils
from usdx_dl.web import state

__all__ = ["router"]

router = APIRouter(prefix="/api")


class ExtendedSongMetadata(models.SongMetadata):
    """Extended song metadata with additional fields for the web API."""

    id: str


@router.get("/songs")
async def api_songs() -> list[ExtendedSongMetadata]:
    """Get a list of all songs."""
    song_list = cli.list.find_songs(
        output_dir=state.server_cfg.output_dir,
        sort_by="artist",
        reverse=False,
    )
    return [
        ExtendedSongMetadata(id=path.name, **meta.model_dump())
        for path, meta in song_list
    ]


class OpenFolderRequest(BaseModel):
    """Request type for the /open-folder endpoint."""

    id: str | None = None

    model_config = models.config


@router.post("/open-folder")
async def api_open_folder(req: OpenFolderRequest):
    """Open the output directory or a specific song directory in the file explorer."""
    path = (
        state.server_cfg.output_dir / str(req.id)
        if req.id
        else state.server_cfg.output_dir
    )
    if not path.exists():
        raise HTTPException(status_code=404, detail="Directory not found.")
    platform_utils.open_with_default_app(path)


@router.get("/state")
async def api_state() -> state.ServerState:
    """Get the current server state."""
    return state.processing_state


@router.get("/settings")
async def api_settings() -> state.Settings:
    """Get the current server settings."""
    plain_settings = state.settings.model_copy()
    plain_settings.pin = None if state.server_cfg.unlocked_settings else "****"
    return plain_settings


@router.post("/settings")
async def api_update_settings(settings: state.Settings):
    """Update the server settings."""
    if state.server_cfg.unlocked_settings:
        settings.pin = state.settings.pin
    elif state.settings.pin and settings.pin != state.settings.pin:
        raise HTTPException(status_code=403, detail="Invalid PIN.")
    state.settings = settings
    state.settings.save()
    config.set("usdb_cookie", state.settings.usdb_cookie)


class PauseRequest(BaseModel):
    """Request type for the /pause endpoint."""

    value: bool

    model_config = models.config


@router.post("/pause")
async def api_pause(req: PauseRequest) -> None:
    """Pause the processing queue."""
    state.settings.pause_processing = req.value
    state.settings.save()


class EnqueueRequest(BaseModel):
    """Request type for the /enqueue endpoint."""

    source: str

    model_config = models.config


@router.post("/enqueue")
async def api_enqueue(req: EnqueueRequest) -> models.PipelineContext:
    """Prepare a download request and add it to the queue."""
    ctx = models.PipelineContext(
        uuid=cli.download.ctx_uuid(),
        url_or_id=req.source,
        usdb_cookie=state.settings.usdb_cookie,
        output_dir=state.server_cfg.output_dir,
        models_dir=state.server_cfg.models_dir,
        stem_model=state.settings.stem_model,
        whisper_model=state.settings.whisper_model,
        no_lyrics=state.settings.no_lyrics,
        no_video=state.settings.no_video,
        non_interactive=True,
    )
    prompt = interactive.NonInteractivePrompt()
    try:
        cli.download.prepare(ctx, prompt)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=str(e)) from e
    state.processing_state.queue.append(ctx)
    state.processing_state.save()
    return ctx


@router.post("/dequeue")
async def api_dequeue(ctx: models.PipelineContext):
    """Remove a queued item from the queue."""
    idx = find_ctx(ctx, state.processing_state.queue)
    del state.processing_state.queue[idx]
    state.processing_state.save()


class MoveRequest(BaseModel):
    """Request type for the /move endpoint."""

    item: models.PipelineContext
    direction: str
    to_end: bool

    model_config = models.config


@router.post("/move")
async def api_move(req: MoveRequest):
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


@router.post("/update")
async def api_update(ctx: models.PipelineContext):
    """Update the metadata of a queued item."""
    ctx.meta = cli.download.update_metadata(ctx)
    idx = find_ctx(ctx, state.processing_state.queue)
    state.processing_state.queue[idx] = ctx
    state.processing_state.save()


@router.post("/retry")
async def api_retry(ctx: models.PipelineContext):
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
