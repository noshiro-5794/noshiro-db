from apps.core.exceptions import BusinessException


class IndexException(BusinessException):

    default_code = 20000
    default_detail = "index error"


class SubjectNotFound(IndexException):

    default_code = 21000
    default_detail = "subject not found"


class SubjectTypeNotSupported(IndexException):

    default_code = 21001
    default_detail = "subject type not supported"


class InvalidEpisodeIds(IndexException):

    default_code = 21100
    default_detail = "invalid episode ids"
