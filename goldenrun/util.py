import importlib
from typing import Any, Callable, Optional

from goldenrun.exceptions import NameLookupError


def get_name_in_module(
    module: str,
    qualname: str,
    attr_getter: Optional[Callable[[Any, str], Any]] = None,
) -> Any:
    """Return the python object specified by qualname in module.

    Raises:
        NameLookupError if the module/qualname cannot be retrieved.
    """
    if attr_getter is None:
        attr_getter = getattr
    try:
        obj = importlib.import_module(module)
    except ModuleNotFoundError:
        raise NameLookupError("No module named '%s'" % (module,))
    walked = []
    for part in qualname.split("."):
        walked.append(part)
        try:
            obj = attr_getter(obj, part)
        except AttributeError:
            raise NameLookupError(
                "Module '%s' has no attribute '%s'" % (module, ".".join(walked))
            )
    return obj
