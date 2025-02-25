from typing import ContextManager, Optional

from goldenrun.config import Config, get_default_config
from goldenrun.tracing import trace_calls


def trace(config: Optional[Config] = None) -> ContextManager[None]:
    """Context manager to trace and log all calls.

    Simple wrapper around `goldenrun.tracing.trace_calls` that uses trace
    logger, code filter, and sample rate from given (or default) config.
    """
    if config is None:
        config = get_default_config()
    return trace_calls(
        logger=config.trace_logger(),
        code_filter=config.code_filter(),
    )
