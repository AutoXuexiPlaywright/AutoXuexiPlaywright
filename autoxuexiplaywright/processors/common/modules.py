from sys import modules
from importlib.util import spec_from_file_location, module_from_spec

# Relative imports
from ...logger import debug
from ...languages import get_language_string


EXTRA_MODULES_NAMESPACE = "autoxuexiplaywright.extra_modules"


def load_modules(filename:str,namespace:str=EXTRA_MODULES_NAMESPACE):
    spec = spec_from_file_location(namespace,filename)
    if spec:
        module = module_from_spec(spec)
        if spec.loader:
            spec.loader.exec_module(module)
            modules[spec.name]=module
        else:
            debug(get_language_string("core-debug-spec-loader-is-none"))
    else:
        debug(get_language_string("core-debug-spec-is-none"))
