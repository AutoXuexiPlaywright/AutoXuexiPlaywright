from inspect import isclass
from sys import modules
from importlib.util import spec_from_file_location, module_from_spec
from typing import Any

# Relative imports
from ...sdk.module import Module, SemVer
from ...logger import debug
from ...languages import get_language_string


EXTRA_MODULES_NAMESPACE = "autoxuexiplaywright.extra_modules"


def _is_module_entrance(obj: Any) -> bool:
    if isclass(obj) and obj != Module and issubclass(obj, Module):
        tobj: type[Module] = obj
        debug(get_language_string("core-debug-checking-module-entrance") %
              (str(tobj.is_entrance()), len(tobj.__subclasses__())))
        if tobj.get_module_api_version() >= SemVer(2, 0, 0):
            debug(get_language_string(
                "core-debug-detected-module-entrance-by-new-method") % str(tobj))
            return obj.is_entrance()

        return len(tobj.__subclasses__()) == 0
    return False


def get_modules_in_file(file: str, namespace: str) -> list[Module]:
    """Get module instances in file

    Args:
        file (str): File path
        namespace (str): The namespace

    Returns:
        list[Module]: The list with all valid module instances
    """
    modules_to_return: list[Module] = []
    spec = spec_from_file_location(namespace, file)
    if spec != None:
        module = module_from_spec(spec)
        if spec.loader != None:
            spec.loader.exec_module(module)
            modules[spec.name] = module
            for name in dir(module):
                if name.startswith("_"):
                    # Skip private modules
                    continue
                value = getattr(module, name)
                if _is_module_entrance(value):
                    try:
                        instance: Module = value()
                    except:
                        pass
                    else:
                        if instance not in modules_to_return:
                            instance.start()
                            modules_to_return.append(instance)
        else:
            debug(get_language_string("core-debug-spec-loader-is-none"))
    else:
        debug(get_language_string("core-debug-spec-is-none"))
    return modules_to_return
