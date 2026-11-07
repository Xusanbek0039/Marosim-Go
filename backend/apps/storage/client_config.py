"""Safe loading of the Google OAuth "Web application" client.

Source order: environment variables (``GOOGLE_OAUTH_CLIENT_ID`` + ``GOOGLE_OAUTH_CLIENT_SECRET``)
win; otherwise the JSON downloaded from Google Cloud Console at ``GOOGLE_OAUTH_CLIENT_FILE``
(default ``backend/credentials/google_oauth_client.json``, git-ignored).

Nothing here ever logs, prints or returns the secret: problems are reported as short codes and
field names only, and ``OAuthClientConfig.__repr__`` masks the values.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

from django.conf import settings

AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"  # noqa: S105 - endpoint URL, not a secret


class ClientConfigError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class OAuthClientConfig:
    client_id: str
    client_secret: str = field(repr=False)
    redirect_uri: str
    project_id: str = ""
    auth_uri: str = AUTH_URI
    token_uri: str = TOKEN_URI
    registered_redirect_uris: tuple[str, ...] = ()
    source: str = "env"

    def __repr__(self) -> str:
        return f"OAuthClientConfig(client_id={self.masked_client_id!r}, source={self.source!r}, project={self.project_id!r})"

    @property
    def masked_client_id(self) -> str:
        return f"{self.client_id[:18]}...{self.client_id[-27:]}" if len(self.client_id) > 40 else "***"

    @property
    def project_number(self) -> str:
        """Leading digits of a client id — the Cloud project number (Google Picker ``appId``)."""
        head = self.client_id.split("-", 1)[0]
        return head if head.isdigit() else ""

    def as_google_client_config(self) -> dict:
        """The dict shape ``google_auth_oauthlib.flow.Flow.from_client_config`` expects."""
        return {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": self.auth_uri,
                "token_uri": self.token_uri,
                "redirect_uris": [self.redirect_uri],
            }
        }


def _from_file(path: Path) -> dict:
    if not path.exists():
        raise ClientConfigError(
            "client_file_missing",
            f"OAuth client JSON topilmadi: {path.name} ni backend/credentials/ papkasiga joylashtiring.",
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ClientConfigError("client_file_invalid", "OAuth client JSON o'qib bo'lmadi (JSON formati noto'g'ri).") from None
    if "web" not in data:
        kind = next(iter(data), "unknown") if isinstance(data, dict) else "unknown"
        raise ClientConfigError(
            "client_type_invalid",
            f"OAuth client turi '{kind}'. Google Cloud'da 'Web application' turidagi client yarating.",
        )
    return data["web"]


def load() -> OAuthClientConfig:
    redirect_uri = settings.GOOGLE_OAUTH_REDIRECT_URI
    if settings.GOOGLE_OAUTH_CLIENT_ID and settings.GOOGLE_OAUTH_CLIENT_SECRET:
        return OAuthClientConfig(
            client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
            client_secret=settings.GOOGLE_OAUTH_CLIENT_SECRET,
            redirect_uri=redirect_uri,
            registered_redirect_uris=(redirect_uri,),
            source="env",
        )

    web = _from_file(Path(settings.GOOGLE_OAUTH_CLIENT_FILE))
    missing = [name for name in ("client_id", "client_secret") if not web.get(name)]
    if missing:
        raise ClientConfigError("client_fields_missing", f"OAuth client JSON'da maydon yo'q: {', '.join(missing)}.")
    registered = tuple(web.get("redirect_uris") or ())
    if redirect_uri not in registered:
        raise ClientConfigError(
            "redirect_uri_mismatch",
            f"Redirect URI {redirect_uri} Google Cloud'dagi 'Authorized redirect URIs' ro'yxatida yo'q.",
        )
    return OAuthClientConfig(
        client_id=web["client_id"],
        client_secret=web["client_secret"],
        redirect_uri=redirect_uri,
        project_id=web.get("project_id", ""),
        auth_uri=web.get("auth_uri") or AUTH_URI,
        token_uri=web.get("token_uri") or TOKEN_URI,
        registered_redirect_uris=registered,
        source="file",
    )


def diagnose() -> dict:
    """Safe-to-display configuration report (status endpoint, ``google_oauth_check``)."""
    from . import vault

    issues = []
    config = None
    try:
        config = load()
    except ClientConfigError as exc:
        issues.append({"code": exc.code, "message": exc.message})
    if not vault.is_configured():
        issues.append(
            {
                "code": "encryption_key_missing",
                "message": "GOOGLE_TOKEN_ENCRYPTION_KEY .env da yo'q yoki noto'g'ri (Fernet kalit kerak).",
            }
        )
    return {
        "configured": not issues,
        "issues": issues,
        "source": config.source if config else None,
        "project_id": config.project_id if config else "",
        "client_id_hint": config.masked_client_id if config else "",
        "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
        "scopes": list(settings.GOOGLE_OAUTH_SCOPES),
    }
