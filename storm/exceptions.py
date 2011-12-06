class TimeoutException(Exception):
    """Exception on timeout"""
    def __repr__(self):
        return "Request timed out"


class BuildErrorException(Exception):
    """Exception on server build"""
    def __repr__(self):
        return "Server failed into error status"


class BadRequest(Exception):
    def __init__(self, message, response_headers=None):
        self.message = message
        self.response_headers = response_headers

    def __str__(self):
        return repr(self.message)
