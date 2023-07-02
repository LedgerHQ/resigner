from typing import Any, Dict, Iterator, Optional
from contextlib import contextmanager

UNKNOWN_ERROR = -13 #: An unknown error occurred

# Exceptions
class NotImplementedError(Exception):
    """
    :class:`HWWError` for :data:`NOT_IMPLEMENTED`
    """

    def __init__(self, msg: str):
        """
        :param msg: The error message
        """
        super.__init__(self, msg, NOT_IMPLEMENTED)

class PSBTSerializationError(Exception):
    """
    :`INVALID_TX`
    """

    def __init__(self, msg: str):
        """
        :param msg: The error message
        """
        super.__init__(self, msg, INVALID_TX)

class BadArgumentError(Exception):
    """
    :`BAD_ARGUMENT`
    """

    def __init__(self, msg: str):
        """
        :param msg: The error message
        """
        super.__init__(self, msg, BAD_ARGUMENT)

@contextmanager
def handle_errors(
    msg: Optional[str] = None,
    result: Optional[Dict[str, Any]] = None,
    code: int = UNKNOWN_ERROR,
    debug: bool = False,
) -> Iterator[None]:
    """
    Context manager to catch all Exceptions and HWWErrors to return them as dictionaries containing the error message and code.

    :param msg: Error message prefix. Attached to the beginning of each error message
    :param result: The dictionary to put the resulting error in
    :param code: The default error code to use for Exceptions
    :param debug: Whether to also print out the traceback for debugging purposes
    """
    if result is None:
        result = {}

    if msg is None:
        msg = ""
    else:
        msg = msg + " "

    try:
        yield

    # Todo: create resigner error class
    except Exception as e:
        result['error'] = msg + e.get_msg()
        result['code'] = e.get_code()
    except Exception as e:
        result['error'] = msg + str(e)
        result['code'] = code
        if debug:
            import traceback
            traceback.print_exc()
    return result


common_err_msgs = {
    "enumerate": ""
}
