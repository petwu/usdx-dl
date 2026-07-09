"""Web worker thread for processing download requests."""

from threading import Event

from usdx_dl import cli, models
from usdx_dl.web import state, ws

stop_event = Event()


def loop() -> None:
    """Worker thread that processes download requests."""
    while not stop_event.is_set():
        output_dir = models.Config.load().output_dir
        # remove any items from the queue that have been deleted from disk
        removed_indices = [
            i
            for i, ctx in enumerate(state.processing_state.queue)
            if not models.SongPaths(output_dir, ctx.song_id).meta.is_file()
        ]
        for i in reversed(removed_indices):
            del state.processing_state.queue[i]

        # filter out not yet reviewed items
        # (the user might want to change metadata before processing)
        queue_indices = [
            i
            for i, ctx in enumerate(state.processing_state.queue)
            if not ctx.errors and ctx.reviewed in (True, None)
        ]

        # in case the server was restarted and the pause setting was changed in between
        if state.server_cfg.pause_processing and state.processing_state.processing:
            state.processing_state.queue.insert(0, state.processing_state.processing)
            state.processing_state.processing = None
            state.processing_state.save()

        # processing paused or empty queue -> wait for a second and check again
        if state.server_cfg.pause_processing or (
            not state.processing_state.processing and len(queue_indices) == 0
        ):
            stop_event.wait(1)
            continue

        # process the next item
        ctx = (
            state.processing_state.processing  #
            or state.processing_state.queue.pop(queue_indices[0])
        )
        state.processing_state.processing = ctx
        state.processing_state.save()
        try:
            cli.download.process(
                ctx,
                output_dir,
                progress_callback=lambda p: ws.broadcast(ws.MsgType.PROGRESS, p),
            )
        except Exception as e:  # pylint: disable=broad-except
            msg = f"Error processing {ctx.url_or_id}: {e}"
            if ctx.errors is None:
                ctx.errors = []
            ctx.errors.append(msg)
            ws.broadcast(ws.MsgType.ERROR, msg)
            # push failed item to the end of the queue for retry
            state.processing_state.queue.append(ctx)

        # done; continue with next item ...
        state.processing_state.processing = None
        state.processing_state.save()
