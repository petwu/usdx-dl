"""Web worker thread for processing download requests."""

from threading import Event

from usdx_dl import cli
from usdx_dl.web import state, ws

stop_event = Event()


def loop() -> None:
    """Worker thread that processes download requests."""
    while not stop_event.is_set():
        queue_indices = [
            i
            for i, ctx in enumerate(state.processing_state.queue)
            if not ctx.errors and ctx.reviewed in (True, None)
        ]
        if state.settings.pause_processing or (
            not state.processing_state.processing and len(queue_indices) == 0
        ):
            stop_event.wait(1)
            continue

        ctx = (
            state.processing_state.processing  #
            or state.processing_state.queue.pop(queue_indices[0])
        )

        state.processing_state.processing = ctx
        state.processing_state.save()
        try:
            cli.download.process(ctx)
        except Exception as e:  # pylint: disable=broad-except
            msg = f"Error processing {ctx.url_or_id}: {e}"
            if ctx.errors is None:
                ctx.errors = []
            ctx.errors.append(msg)
            ws.broadcast(ws.MsgType.ERROR, msg)
            state.processing_state.queue.append(ctx)
        state.processing_state.processing = None
        state.processing_state.save()
