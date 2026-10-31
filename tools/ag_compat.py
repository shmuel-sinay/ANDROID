"""Small fixes for androguard when reading Android platform dex files.

framework.jar carries hidden-API flag values that androguard's enums do not
list (for example domain flag 3). Unknown values become pseudo members
instead of raising ValueError. Import this module before loading any dex.
"""
from loguru import logger

logger.remove()

from androguard.core.dex import HiddenApiClassDataItem as _H  # noqa: E402


def _allow_unknown(enum_cls):
    def _missing_(cls, value):
        member = int.__new__(cls, value)
        member._name_ = f"UNKNOWN_{value}"
        member._value_ = value
        return member
    enum_cls._missing_ = classmethod(_missing_)


_allow_unknown(_H.DomapiApiFlag)
_allow_unknown(_H.RestrictionApiFlag)
