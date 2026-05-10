from rest_framework import status
from rest_framework.views import exception_handler
from rest_framework.exceptions import ValidationError

from apps.core.response import APIResponse
from apps.core.exceptions import BusinessException


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if isinstance(exc, BusinessException):
        return APIResponse(
            code=exc.code, message=str(exc.detail), data=None, status=exc.status_code
        )

    if isinstance(exc, ValidationError):
        return APIResponse(
            code=40000,
            message="validation error",
            data=response.data if response else None,
            status=status.HTTP_400_BAD_REQUEST,
        )

    if response is not None:
        detail = None
        if isinstance(response.data, dict):
            detail = response.data.get("detail")
        return APIResponse(
            code=response.status_code * 100,
            message=str(detail or "request failed"),
            data=response.data,
            status=response.status_code,
        )

    return APIResponse(
        code=50000,
        message="internal error",
        data=None,
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
