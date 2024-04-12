from abc import ABC, abstractmethod
from typing import NamedTuple, final, TypeVar
from typing_extensions import deprecated


T=TypeVar("T",bound="Module")

class SemVer(NamedTuple):
    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return "{}.{}.{}".format(self.major, self.minor, self.patch)


class Module(ABC):
    @final
    @classmethod
    @deprecated("Remove in the future, always return False now.")
    def is_entrance(cls) -> bool:
        """If this class is marked to be the entrance of module

        Returns:
            bool: If it is the entrance, False if is not marked
        """
        return False

    @final
    @staticmethod
    def get_module_api_version() -> SemVer:
        return SemVer(2, 1, 0)

    @property
    @abstractmethod
    def name(self) -> str: ...  # The name of your module

    @property
    @abstractmethod
    def author(self) -> str: ...  # The author of your module

    def start(self):  # Called when it is started
        pass

    def close(self):  # Called when it is going to be closed
        pass


_modules:set[Module]=set()

def module_entrance(cls: type[T]) -> type[T]:
    """Register the module's entrance

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
    instance=cls()
    if instance not in _modules:
        instance.start()
        _modules.add(instance)
    return cls

def get_modules_by_type(t: type[T] = Module) -> list[T]:
    return [m for m in _modules if isinstance(m,t)]
