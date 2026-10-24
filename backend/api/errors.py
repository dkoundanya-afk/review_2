"""One error shape for the whole API: {"error": "<reason_code>", ...extra}.
The frontend maps reason codes to translated text (HARD RULE 7); the server never sends UI prose."""
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_handler


class ApiError(Exception):
    def __init__(self, status: int, error: str, **extra):
        super().__init__(error)
        self.status, self.error, self.extra = status, error, extra


_CODES = {400: "bad_request", 401: "not_authenticated", 403: "forbidden", 404: "not_found",
          405: "method_not_allowed", 415: "unsupported_media_type", 429: "rate_limited"}


def handler(exc, context):
    if isinstance(exc, ApiError):
        return Response({"error": exc.error, **exc.extra}, status=exc.status)
    resp = drf_handler(exc, context)
    if resp is not None:
        resp.data = {"error": _CODES.get(resp.status_code, "bad_request")}
    return resp
