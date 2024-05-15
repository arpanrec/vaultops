import sys
from typing import Callable, Optional


class ExitHooks:
    """
    Class to hook sys.exit() and sys.excepthook() calls.
    """

    exit_code: int = 0
    exception: Optional[Exception] = None
    _orig_exit: Optional[Callable] = None
    _orig_exc_handler: Optional[Callable] = None

    def hook(self):
        """
        Hook sys.exit() and sys.excepthook() calls.
        """
        self._orig_exit = sys.exit
        self._orig_exc_handler = sys.excepthook
        sys.exit = self.exit  # type: ignore
        sys.excepthook = self.exc_handler

    def exit(self, code: Optional[int], *args, **kwargs):
        """
        Hook for sys.exit() calls.
        Args:
            code (int): Exit code.
            args: Additional arguments.
            kwargs: Additional keyword arguments.
        """
        if code is not None:
            self.exit_code = code
        if self._orig_exit:
            self._orig_exit(code, *args, **kwargs)

    def exc_handler(self, exc_type, exc, *args, **kwargs):
        """
        Hook for sys.excepthook() calls.
        Args:
            exc_type: Exception type.
            exc: Exception object.
            args: Additional arguments.
            kwargs: Additional keyword arguments.
        """
        self.exception = exc
        if self._orig_exc_handler:
            self._orig_exc_handler(exc_type, exc, *args, **kwargs)
