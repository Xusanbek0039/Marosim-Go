"""Idempotent Drive folder tree (Phase D):  MarosimGo / Studio_<uuid> / Ceremony_<uuid> / {Photos, Videos}.

Callers pass logical keys and names; this module never imports domain apps. A folder is looked up
in this order: DB cache → an existing app-created folder with that name under the parent (recovers a
lost cache) → create. A concurrent creator that loses the unique-key race deletes its duplicate.
Folder names contain ids only — never people's names or phone numbers.
"""

import logging

from django.db import IntegrityError, transaction

from .google import GoogleError
from .models import DriveFolder, StorageConnection
from .services import StorageError, access_credentials, connection, gateway

logger = logging.getLogger("apps.storage")

ROOT_NAME = "MarosimGo"


def _account(conn: StorageConnection) -> str:
    if not conn.account_email:
        raise StorageError("not_connected")
    return conn.account_email


def ensure_root(creds, conn: StorageConnection | None = None) -> str:
    """The connection's root folder; created by the app when none was picked."""
    conn = conn or connection()
    if conn.root_folder_id:
        return conn.root_folder_id
    folder_id = _ensure(creds, conn, key="root", name=ROOT_NAME, parent_id=None)
    StorageConnection.objects.filter(pk=conn.pk, root_folder_id="").update(
        root_folder_id=folder_id, root_folder_name=ROOT_NAME
    )
    conn.refresh_from_db(fields=["root_folder_id", "root_folder_name"])
    return conn.root_folder_id


def _ensure(creds, conn, *, key: str, name: str, parent_id: str | None) -> str:
    account = _account(conn)
    row = DriveFolder.objects.filter(account_email=account, key=key).first()
    if row is not None:
        return row.folder_id
    gw = gateway()
    try:
        existing = gw.find_child_folder(creds, name, parent_id) if parent_id else None
        folder_id = existing or gw.create_folder(creds, name, parent_id)["id"]
    except GoogleError as exc:
        raise StorageError(exc.code) from None
    try:
        with transaction.atomic():
            DriveFolder.objects.create(
                account_email=account, key=key, folder_id=folder_id, parent_id=parent_id or "", name=name
            )
    except IntegrityError:
        winner = DriveFolder.objects.get(account_email=account, key=key)
        if not existing and winner.folder_id != folder_id:
            try:
                gw.delete_file(creds, folder_id)  # our duplicate lost the race
            except GoogleError:
                logger.warning("could not delete duplicate Drive folder %s", folder_id)
        return winner.folder_id
    return folder_id


def ensure_path(segments: list[tuple[str, str]], creds=None) -> tuple[str, object]:
    """Create/resolve ``[(key, name), …]`` below the root; returns (leaf folder id, credentials).

    Keys are cumulative so every level is unique: ``studio:x``, ``studio:x/ceremony:y`` …
    """
    conn = connection()
    creds = creds or access_credentials(conn)
    parent = ensure_root(creds, conn)
    for key, name in segments:
        parent = _ensure(creds, conn, key=key, name=name, parent_id=parent)
    return parent, creds


def forget(prefix: str) -> int:
    """Drop cached ids under ``prefix`` (e.g. after Drive reports the folder ``not_found``)."""
    conn = connection()
    deleted, _ = DriveFolder.objects.filter(account_email=conn.account_email, key__startswith=prefix).delete()
    return deleted
