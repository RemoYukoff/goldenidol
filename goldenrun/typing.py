import types
from collections import defaultdict
from typing import (
    Any,
    Callable,
    DefaultDict,
    Dict,
    Iterator,
    List,
    Set,
    Tuple,
    Type,
)


_BUILTIN_CALLABLE_TYPES = (
    types.FunctionType,
    types.LambdaType,
    types.MethodType,
    types.BuiltinMethodType,
    types.BuiltinFunctionType,
)


def get_type(obj):
    """Return the static type that would be used in a type hint"""
    if isinstance(obj, type):
        return Type[obj]
    elif isinstance(obj, _BUILTIN_CALLABLE_TYPES):
        return Callable
    elif isinstance(obj, types.GeneratorType):
        return Iterator[Any]
    elif isinstance(obj, list):
        return List[Any]
    elif isinstance(obj, set):
        return Set[Any]
    elif isinstance(obj, dict):
        return Dict(Any, Any)
    elif isinstance(obj, defaultdict):
        return DefaultDict[Any, Any]
    elif isinstance(obj, tuple):
        return Tuple[Any]
