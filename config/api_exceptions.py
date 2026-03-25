import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from apps.bookings.exceptions import BookingConflictError, BookingValidationError

api_logger = logging.getLogger("booking_management.api")

security_logger = logging.getLogger("booking_management.security")


def _get_request_log_context(context) -> dict:
    request = context.get("request")

    if request is None:
        return {}

    user = getattr(request, "user", None)

    user_id = None

    if user is not None and getattr(user, "is_authenticated", False):
        user_id = user.pk

    return {"method": request.method, "path": request.path, "user_id": user_id}


def api_exception_handler(exc, context):
    log_context = _get_request_log_context(context)

    if isinstance(exc, BookingConflictError):
        api_logger.info(
            "booking_conflict",
            extra={
                **log_context,
                "status_code": (status.HTTP_409_CONFLICT),
                "error_code": exc.code,
            },
        )

        return Response(
            {
                "detail": exc.message,
                "code": exc.code,
            },
            status=status.HTTP_409_CONFLICT,
        )

    if isinstance(exc, BookingValidationError):
        api_logger.info(
            "booking_validation_failed",
            extra={
                **log_context,
                "status_code": (status.HTTP_400_BAD_REQUEST),
                "error_code": exc.code,
            },
        )

        return Response(
            {
                "detail": exc.message,
                "code": exc.code,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    response = drf_exception_handler(exc, context)

    if response is not None:
        if response.status_code in {
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        }:
            security_logger.warning(
                "api_access_denied",
                extra={
                    **log_context,
                    "status_code": (response.status_code),
                },
            )

        return response

    api_logger.error(
        "unhandled_api_exception",
        extra={**log_context, "status_code": (status.HTTP_500_INTERNAL_SERVER_ERROR)},
        exc_info=(
            type(exc),
            exc,
            exc.__traceback__,
        ),
    )

    return Response(
        {"detail": "Internal server error.", "code": "internal_error"},
        status=(status.HTTP_500_INTERNAL_SERVER_ERROR),
    )
