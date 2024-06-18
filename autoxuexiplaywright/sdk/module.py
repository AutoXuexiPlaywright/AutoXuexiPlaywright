"""Base Module class."""

from abc import ABC
from abc import abstractmethod
from typing import TypeVar
from typing import NamedTuple
from typing import final
from typing_extensions import override
from typing_extensions import deprecated


T = TypeVar("T", bound="Module")


class SemVer(NamedTuple):
    """NamedTuple which can storage version status."""

    major: int
    minor: int
    patch: int

    @override
    def __str__(self) -> str:
        return "{}.{}.{}".format(self.major, self.minor, self.patch)


class Module(ABC):
    """Base Module class."""

    @final
    @classmethod
    @deprecated("Remove in the future, always return False now.")
    def is_entrance(cls) -> bool:
        """If this class is marked to be the entrance of module.

        Returns:
            bool: If it is the entrance, False if is not marked
        """
        return False

    @final
    @staticmethod
    def get_module_api_version() -> SemVer:
        """Get the module's API version."""
        return SemVer(2, 1, 0)

    @property
    @abstractmethod
    def name(self) -> str:
        """The name of the module."""

    @property
    @abstractmethod
    def author(self) -> str:
        """The author of the module."""

    def start(self):
        """Called when module is started."""

    def close(self):
        """Called when module is going to be closed."""


_modules: set[Module] = set()


def module_entrance(cls: type[T]) -> type[T]:
    """Register the module's entrance.

    Args:
        cls (type[Module]): the module's entrance'

    Returns:
        type[Module]: The pointer to the cls

    Examples:
        ```python
        @module_entrance
        class MyModule(Module):
            pass
        ```
    """
    instance = cls()
    if instance not in _modules:
        instance.start()
        _modules.add(instance)
    return cls


def get_modules_by_type(t: type[T] = Module) -> list[T]:
    """Get modules by module type.

    Args:
        t(type[T]): The module's type

    Returns:
        list[T]: All modules which is the instance of T
    """
    return [m for m in _modules if isinstance(m, t)]
