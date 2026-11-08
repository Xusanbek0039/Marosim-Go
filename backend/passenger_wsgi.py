"""cPanel "Setup Python App" (Phusion Passenger) entry point.

Application root = this backend/ folder, startup file = passenger_wsgi.py, entry point = application.
Serves the API (/api/v1/) and the Super Admin panel (everything else) — see config/panel.py.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
