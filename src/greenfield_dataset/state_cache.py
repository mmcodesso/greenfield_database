from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from greenfield_dataset.settings import GenerationContext


T = TypeVar("T")


def drop_context_attributes(context: GenerationContext, attribute_names: list[str]) -> None:
    for attribute_name in attribute_names:
        if hasattr(context, attribute_name):
            delattr(context, attribute_name)


def get_or_build_cache(
    context: GenerationContext,
    attribute_name: str,
    builder: Callable[[], T],
) -> T:
    cached = getattr(context, attribute_name, None)
    if cached is not None:
        return cached
    cached = builder()
    setattr(context, attribute_name, cached)
    return cached
