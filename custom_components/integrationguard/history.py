"""Keeps a record of what changed, in its own SQLite file.

Not in the recorder database: this is a handful of rows a day that should
survive a purge, and it keeps the recorder free of rows nothing else reads.
"""

from __future__ import annotations

from datetime import timedelta
import json
import logging
from pathlib import Path
import sqlite3
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

FILE_NAME = f"{DOMAIN}_history.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    kind TEXT NOT NULL,
    key TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT '',
    previous TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT '',
    detail TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events (ts);
CREATE INDEX IF NOT EXISTS idx_events_key ON events (key);
"""


class History:
    """Appends events and answers questions about them."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Remember where the file lives."""
        self._hass = hass
        self._path = Path(hass.config.path(FILE_NAME))
        self._ready = False

    async def async_setup(self) -> None:
        """Create the file and its schema if they are not there yet."""
        await self._hass.async_add_executor_job(self._setup)

    def _setup(self) -> None:
        """Run the schema. Runs in the executor."""
        try:
            with self._connect() as connection:
                connection.executescript(SCHEMA)
            self._ready = True
        except sqlite3.Error:
            _LOGGER.exception("Could not open the history database at %s", self._path)

    def _connect(self) -> sqlite3.Connection:
        """Open a connection. Runs in the executor."""
        connection = sqlite3.connect(self._path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    async def async_record(self, events: list[dict[str, Any]]) -> None:
        """Append a batch of events."""
        if not events or not self._ready:
            return
        await self._hass.async_add_executor_job(self._record, events)

    def _record(self, events: list[dict[str, Any]]) -> None:
        """Insert the rows. Runs in the executor."""
        now = dt_util.utcnow().isoformat()
        rows = [
            (
                event.get("ts") or now,
                event.get("kind", "status"),
                event.get("key", ""),
                event.get("name", ""),
                event.get("category", ""),
                event.get("previous", ""),
                event.get("status", ""),
                json.dumps(event.get("detail") or {}),
            )
            for event in events
        ]
        try:
            with self._connect() as connection:
                connection.executemany(
                    "INSERT INTO events "
                    "(ts, kind, key, name, category, previous, status, detail) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    rows,
                )
        except sqlite3.Error:
            _LOGGER.exception("Could not write %s history events", len(rows))

    async def async_query(
        self, *, limit: int = 200, key: str | None = None, kind: str | None = None
    ) -> list[dict[str, Any]]:
        """Return the most recent events, newest first."""
        if not self._ready:
            return []
        return await self._hass.async_add_executor_job(self._query, limit, key, kind)

    def _query(
        self, limit: int, key: str | None, kind: str | None
    ) -> list[dict[str, Any]]:
        """Read the rows. Runs in the executor."""
        sql = "SELECT * FROM events"
        clauses: list[str] = []
        params: list[Any] = []
        if key:
            clauses.append("key = ?")
            params.append(key)
        if kind:
            clauses.append("kind = ?")
            params.append(kind)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(max(1, min(limit, 1000)))
        try:
            with self._connect() as connection:
                rows = connection.execute(sql, params).fetchall()
        except sqlite3.Error:
            _LOGGER.exception("Could not read the history")
            return []
        return [
            {
                # A sqlite3.Row iterates over its values, so the column
                # names have to come from keys().
                **{k: row[k] for k in row.keys() if k != "detail"},  # noqa: SIM118
                "detail": _load(row["detail"]),
            }
            for row in rows
        ]

    async def async_purge(self, retention_days: int) -> None:
        """Delete everything older than the configured retention."""
        if not self._ready or retention_days <= 0:
            return
        await self._hass.async_add_executor_job(self._purge, retention_days)

    def _purge(self, retention_days: int) -> None:
        """Delete the old rows. Runs in the executor."""
        cutoff = (dt_util.utcnow() - timedelta(days=retention_days)).isoformat()
        try:
            with self._connect() as connection:
                connection.execute("DELETE FROM events WHERE ts < ?", (cutoff,))
        except sqlite3.Error:
            _LOGGER.exception("Could not purge the history")

    async def async_remove(self) -> None:
        """Delete the file when the integration is removed."""
        await self._hass.async_add_executor_job(self._remove)

    def _remove(self) -> None:
        """Unlink the file. Runs in the executor."""
        self._path.unlink(missing_ok=True)


def _load(value: str) -> dict[str, Any]:
    """Return the stored detail, tolerating anything unreadable."""
    try:
        loaded = json.loads(value)
    except (TypeError, ValueError):
        return {}
    return loaded if isinstance(loaded, dict) else {}
