"""Off-request persistence of ``RequestLog`` rows.

The middleware only builds an unsaved model instance and hands it to :func:`submit`. In async
mode (default) a single daemon thread per process batches rows into ``bulk_create`` every
``FLUSH_INTERVAL_SECONDS`` or ``BATCH_SIZE`` rows, so a request never waits on a metrics write.
The queue is bounded: if the database is unavailable rows are dropped, never the request.
Retention is enforced from the same thread at most once per ``PRUNE_INTERVAL_SECONDS``.
"""

import atexit
import logging
import queue
import threading
import time
from datetime import timedelta

from django.conf import settings
from django.db import close_old_connections
from django.utils import timezone

from .models import RequestLog

logger = logging.getLogger("apps.monitoring")


def cfg() -> dict:
    return settings.MONITORING


class _Writer:
    def __init__(self):
        self._queue: queue.Queue | None = None
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._last_prune = 0.0
        self.dropped = 0

    # ------------------------------------------------------------------ public
    def submit(self, entry: RequestLog) -> None:
        if not cfg()["ASYNC"]:
            self._write([entry])
            return
        self._ensure_thread()
        try:
            self._queue.put_nowait(entry)
        except queue.Full:
            self.dropped += 1

    def flush(self) -> None:
        """Write everything queued so far (tests, shutdown)."""
        if self._queue is None:
            return
        batch = []
        while True:
            try:
                batch.append(self._queue.get_nowait())
            except queue.Empty:
                break
        if batch:
            self._write(batch)

    # ----------------------------------------------------------------- internals
    def _ensure_thread(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._queue = self._queue or queue.Queue(maxsize=cfg()["QUEUE_MAX"])
            self._thread = threading.Thread(target=self._run, name="request-log-writer", daemon=True)
            self._thread.start()

    def _run(self) -> None:
        interval = cfg()["FLUSH_INTERVAL_SECONDS"]
        batch_size = cfg()["BATCH_SIZE"]
        while True:
            batch = []
            deadline = time.monotonic() + interval
            while len(batch) < batch_size:
                timeout = deadline - time.monotonic()
                if timeout <= 0:
                    break
                try:
                    batch.append(self._queue.get(timeout=timeout))
                except queue.Empty:
                    break
            if batch:
                self._write(batch)
            self._maybe_prune()

    def _write(self, batch: list[RequestLog]) -> None:
        try:
            RequestLog.objects.bulk_create(batch, batch_size=cfg()["BATCH_SIZE"])
        except Exception:  # noqa: BLE001 - metrics must never break anything
            self.dropped += len(batch)
            logger.warning("request log write failed; %d rows dropped", len(batch), exc_info=True)
        finally:
            if threading.current_thread() is self._thread:
                close_old_connections()

    def _maybe_prune(self) -> None:
        now = time.monotonic()
        if now - self._last_prune < cfg()["PRUNE_INTERVAL_SECONDS"]:
            return
        self._last_prune = now
        try:
            prune()
        except Exception:  # noqa: BLE001
            logger.warning("request log pruning failed", exc_info=True)
        finally:
            close_old_connections()


def prune(now=None) -> int:
    """Apply the retention policy (age, then row cap). Returns the number of deleted rows."""
    now = now or timezone.now()
    deleted, _ = RequestLog.objects.filter(created_at__lt=now - timedelta(days=cfg()["RETENTION_DAYS"])).delete()
    max_rows = cfg()["MAX_ROWS"]
    if max_rows:
        cutoff = RequestLog.objects.order_by("-id").values_list("id", flat=True)[max_rows : max_rows + 1]
        cutoff_id = next(iter(cutoff), None)
        if cutoff_id is not None:
            more, _ = RequestLog.objects.filter(id__lte=cutoff_id).delete()
            deleted += more
    return deleted


writer = _Writer()
atexit.register(writer.flush)
