"""FastAPI middleware for request correlation IDs and request-level logging."""

from __future__ import annotations

import time
import uuid
from contextvars import ContextVar

from fastapi import Request, Response
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    return request_id_var.get()


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Attach a unique request ID to every incoming request.

    - Reads X-Request-ID from the incoming header (if provided by a gateway),
      otherwise generates a new UUID.
    - Sets it in a ContextVar so loguru and route code can access it.
    - Returns it in the response header.
    - Logs request start/end with method, path, status, and latency.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        request_id_var.set(rid)

        start = time.perf_counter()
        method = request.method
        path = request.url.path

        logger.info(
            "[rid={}] {} {} started", rid, method, path
        )

        try:
            response = await call_next(request)
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.error(
                "[rid={}] {} {} failed after {:.1f}ms: {}",
                rid, method, path, elapsed_ms, exc,
            )
            raise

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "[rid={}] {} {} completed: status={} latency={:.1f}ms",
            rid, method, path, response.status_code, elapsed_ms,
        )

        response.headers["X-Request-ID"] = rid
        return response
