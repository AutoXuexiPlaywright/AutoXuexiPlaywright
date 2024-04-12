# DEPRECATED: Use sub-packages in autoxuexiplaywright.sdk instead
from typing import Callable

from ..languages import get_language_string
from ..logger import warning
from .module import Module, SemVer
from .answer import AnswerSource as AnswerSourceNew


def _override_version(version: SemVer):
    """Override version to a specific SemVer

    Args:
        version (SemVer): The version to override to

    Returns:
        Callable[[type[Module]],type[Module]]: A wrapper function to do the override job

    Examples:
        ```python
        @_override_version(SemVer(1,0,0))
        class MyModule(Module):
            ...
        ```
    """
    def override_wrapper(cls: type[Module]):

        @staticmethod
        def get_module_api_version():
            return version

        def extra_start(instance: Module):
            warning(get_language_string("core-warning-deprecated-module-version") %
                    (str(instance.get_module_api_version()), instance.name, instance.author))

        if version <= cls.get_module_api_version():
            orig_start: Callable[[Module], None] = getattr(cls, "start")
            if callable(orig_start):

                def new_start(instance: Module):
                    orig_start(instance)
                    extra_start(instance)

                setattr(cls, "start", new_start)
        setattr(cls, "get_module_api_version", get_module_api_version)
        return cls
    return override_wrapper


@_override_version(SemVer(1, 0, 0))
class AnswerSource(AnswerSourceNew):
    pass