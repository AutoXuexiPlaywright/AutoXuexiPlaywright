"""Dummy sdk package for compatibility reasons.

DEPRECATED: Use sub-packages in autoxuexiplaywright.sdk instead
"""

from typing import Callable
from .answer import AnswerSource as AnswerSourceNew
from .module import Module
from .module import SemVer
from ..logger import warning
from ..languages import get_language_string


def _override_version(version: SemVer) -> Callable[[type[Module]], type[Module]]:
    """Override version to a specific SemVer.

    Args:
        version (SemVer): The version to override to

    Returns:
        Callable[[type[Module]],type[Module]]: A wrapper function to do the override job

    Examples:
        ```python
        @_override_version(SemVer(1, 0, 0))
        class MyModule(Module): ...
        ```
    """

    def override_wrapper(cls: type[Module]) -> type[Module]:
        @staticmethod
        def get_module_api_version() -> SemVer:
            return version

        def extra_start(instance: Module):
            warning(
                get_language_string("core-warning-deprecated-module-version")
                % (str(instance.get_module_api_version()), instance.name, instance.author),
            )

        if version <= cls.get_module_api_version():
            orig_start: Callable[[Module], None] = cls.start
            if callable(orig_start):

                def new_start(self: Module):
                    orig_start(self)
                    extra_start(self)

                cls.start = new_start
        cls.get_module_api_version = get_module_api_version  # type: ignore
        return cls

    return override_wrapper


@_override_version(SemVer(1, 0, 0))
class AnswerSource(AnswerSourceNew):
    """Dummy AnswerSource for compatibility reasons."""
