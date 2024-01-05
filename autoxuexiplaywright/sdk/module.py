from abc import ABC, abstractmethod
from typing import NamedTuple, final


class SemVer(NamedTuple):
    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return "%d.%d.%d".format(self.major, self.minor, self.patch)


class Module(ABC):
    @final
    @classmethod
    def is_entrance(cls) -> bool:
        """If this class is marked to be the entrance of module

        Returns:
            bool: If it is the entrance, False if is not marked
        """
        return _entrances_map.get(id(cls), False)

    @final
    @staticmethod
    def get_module_api_version() -> SemVer:
        return SemVer(2, 0, 0)

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


_entrances_map: dict[int, bool] = {}


def module_entrance(cls: type[Module]) -> type[Module]:
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
    _entrances_map[id(cls)] = True
    return cls