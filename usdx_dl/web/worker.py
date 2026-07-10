"""Web worker thread for processing download requests."""
# pylint: disable=global-statement,invalid-name

import multiprocessing
from threading import Event, Thread

from usdx_dl import ansi, cli, models
from usdx_dl.web import state, ws

__all__ = ["start", "stop", "pause", "resume", "cancel"]


stop_event = Event()
msg_queue = multiprocessing.Queue()  # type: ignore
worker_thread: Thread | None = None
msg_queue_thread: Thread | None = None
current_process: multiprocessing.Process | None = None


def download_job(
    ctx,
    output_dir,
    msg_queue: multiprocessing.Queue,  # pylint: disable=redefined-outer-name
) -> None:
    """Run the download job in a separate process."""
    try:
        msg_queue.put((ws.MsgType.PROGRESS, {"type": "worker", "progress": 0.0}))
        cli.download.process(
            ctx,
            output_dir,
            progress_callback=lambda p: msg_queue.put(
                (ws.MsgType.PROGRESS, {"what": "worker", "progress": p})
            ),
        )
    except Exception as e:  # pylint: disable=broad-exception-caught
        msg_queue.put((ws.MsgType.ERROR, f"Error processing {ctx.url_or_id}: {e}"))


def msg_queue_loop():
    """Worker thread that processes messages from the download worker process."""
    while not stop_event.is_set():
        try:
            args = msg_queue.get(timeout=0.1)
            ws.broadcast(*args)
        except Exception:  # pylint: disable=broad-exception-caught
            pass


def worker_loop() -> None:
    """Worker thread that processes download requests."""
    global current_process

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

        # processing paused or empty queue -> wait and check again
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

        current_process = multiprocessing.Process(
            target=download_job,
            args=(ctx, output_dir, msg_queue),
            daemon=True,
        )
        current_process.start()
        current_process.join()  # blocks until done or killed
        exit_code = current_process.exitcode
        current_process = None

        if exit_code != 0 and not stop_event.is_set():
            # process was cancelled or crashed
            if exit_code is not None and exit_code < 0:
                print()
                print(
                    ansi.RED
                    + f"Processing of {ctx.url_or_id} was cancelled. "
                    + "Putting it back into the queue for retry."
                    + ansi.RESET
                )
                # negative exit code = killed by signal (i.e. cancel())
                # put the current item back into the queue
                ctx = state.processing_state.processing
                if len(state.processing_state.queue) == 0:
                    state.server_cfg.pause_processing = True
                if state.server_cfg.pause_processing:
                    state.processing_state.queue.insert(0, ctx)
                else:
                    state.processing_state.queue.append(ctx)
                state.processing_state.processing = None
                state.processing_state.save()
                continue

            # crashed with an exception — re-queue for retry
            msg = f"Error processing {ctx.url_or_id}: process exited with code {exit_code}"
            if ctx.errors is None:
                ctx.errors = []
            ctx.errors.append(msg)
            ws.broadcast(ws.MsgType.ERROR, msg)
            # push failed item to the end of the queue for retry
            state.processing_state.queue.append(ctx)

        # done; continue with next item ...
        state.processing_state.processing = None
        state.processing_state.save()


def start() -> None:
    """Start the worker thread."""
    global worker_thread, msg_queue_thread
    msg_queue_thread = Thread(target=msg_queue_loop, daemon=True)
    msg_queue_thread.start()
    worker_thread = Thread(target=worker_loop, daemon=True)
    worker_thread.start()


def stop(timeout: float = 3.0) -> None:
    """Stop the worker thread and any running child process."""
    stop_event.set()
    if current_process and current_process.is_alive():
        current_process.kill()
    if worker_thread:
        worker_thread.join(timeout=timeout)
    if msg_queue_thread:
        msg_queue_thread.join(timeout=timeout)


def pause() -> None:
    """Pause processing of the queue."""
    state.server_cfg.pause_processing = True


def resume() -> None:
    """Resume processing of the queue."""
    state.server_cfg.pause_processing = False


def cancel() -> None:
    """Cancel the current processing item."""
    if not state.processing_state.processing:
        return

    # kill the child process — loop() will detect the negative exit code
    if current_process and current_process.is_alive():
        current_process.kill()
