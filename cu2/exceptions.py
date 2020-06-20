from requests.exceptions import ConnectionError
from sqlalchemy.exc import IntegrityError as DatabaseIntegrityError


class Cu2Exception(Exception):
    """Base class for all cu2 exceptions."""

    def __init__(self, message=''):
        self.message = message

    def __str__(self):
        return repr(self.message)


class LoginError(Cu2Exception):
    pass


class ScrapingError(Cu2Exception):
    pass


class ConfigError(Cu2Exception):
    """Exception that is thrown when cu2 encounters a malformed configuration
    file. Accepts a string representing the raw text of the configuration file,
    the cursor position as a (row, column) tuple and a message.
    """

    def __init__(self, config, cursor, message=''):
        self.config = config
        self.cursor = cursor
        super().__init__(message)
