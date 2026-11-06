import mimetypes

from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "apps.core"
    label = "core"

    def ready(self):
        # Windows' registry often lacks WEBP; uploads are always stored as .webp.
        mimetypes.add_type("image/webp", ".webp")
