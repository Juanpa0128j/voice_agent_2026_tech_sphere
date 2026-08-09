"""Standalone admin FastAPI app.

The full set of admin endpoints (``/admin/documents``, ``/admin/delete``,
``/admin/upload``, ``/admin/reindex``) lives in :mod:`backend.api_app` so
the public FastAPI ``TestClient`` can be constructed from a single import.
This module re-exports the same ``app`` for users that want to run the
admin console on its own port.
"""
from backend.api_app import app

__all__ = ["app"]
