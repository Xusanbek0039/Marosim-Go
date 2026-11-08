"""Burn the MarosimGo logo into queued videos (back-fill, retries; or a standalone worker with --loop)."""

import time

from django.core.management.base import BaseCommand

from apps.media import watermark
from apps.media.watermark_jobs import drain


class Command(BaseCommand):
    help = "Produce watermarked copies of videos waiting for one."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=None, help="Stop after this many videos.")
        parser.add_argument("--loop", action="store_true", help="Keep running; poll the queue every 30 s.")

    def handle(self, *args, limit=None, loop=False, **options):
        if not watermark.ffmpeg_bin():
            self.stderr.write(self.style.ERROR("ffmpeg topilmadi (PATH)."))
            return
        while True:
            done = drain(limit)
            self.stdout.write(self.style.SUCCESS(f"{done} video(s) processed."))
            if not loop:
                return
            time.sleep(30)
