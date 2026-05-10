from rest_framework import status
from rest_framework.exceptions import APIException


class BusinessException(APIException):

    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 10000
    default_detail = "business error"

    def __init__(self, detail=None, code=None):
        if detail is None:
            detail = self.default_detail
        if code is None:
            code = self.default_code
        self.detail = detail
        self.code = code
