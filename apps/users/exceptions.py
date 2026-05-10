from apps.core.exceptions import BusinessException


class UserException(BusinessException):

    default_code = 10000
    default_detail = "user error"


class EmailSendTooFrequent(UserException):

    default_code = 11000
    default_detail = "email send too frequent"


class InvalidVerifyCode(UserException):

    default_code = 11001
    default_detail = "invalid verify code"


class VerifyCodeExpired(UserException):

    default_code = 11002
    default_detail = "verify code expired"


class EmailAlreadyExists(UserException):

    default_code = 11100
    default_detail = "email already exists"


class InvalidEmailOrPassword(UserException):

    default_code = 11200
    default_detail = "invalid email or password"


class UserNotFound(UserException):

    default_code = 11201
    default_detail = "user not found"
