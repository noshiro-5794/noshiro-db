"""Permission failures that HTTP adapters translate into community problems."""


class InteractionBlocked(PermissionError):
    pass


class CommentPermissionDenied(PermissionError):
    pass
