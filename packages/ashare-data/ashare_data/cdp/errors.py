"""CDP collector errors."""


class CdpError(RuntimeError):
    """Base error for CDP collector failures."""


class CdpUnavailableError(CdpError):
    """Raised when the Chrome CDP endpoint or helper is unavailable."""


class CdpNavigationError(CdpError):
    """Raised when a page cannot be opened or navigated."""


class CdpFetchError(CdpError):
    """Raised when page-context fetch fails."""


class CdpEvalError(CdpError):
    """Raised when page-context JavaScript evaluation fails."""
