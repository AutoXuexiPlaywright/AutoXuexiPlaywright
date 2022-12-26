from sys import modules
from typing import TypeVar, Any
from importlib.util import spec_from_file_location, module_from_spec

from autoxuexiplaywright.sdk import AnswerSource
from autoxuexiplaywright.defines.core import MOD_EXT, EXTRA_ANSWER_SOURCES_NAMESPACE


T = TypeVar("T")


def get_modules_in_file(file: str) -> list[AnswerSource]:
    modules_to_return: list[AnswerSource] = []
    if file.endswith(MOD_EXT):
        mod_namespce = ".".join(
            [EXTRA_ANSWER_SOURCES_NAMESPACE, "external_%d" % (len(modules_to_return)+1)])
        spec = spec_from_file_location(mod_namespce, file)
        if spec is not None:
            module = module_from_spec(spec)
            if spec.loader is not None:
                modules[spec.name] = module
                spec.loader.exec_module(module)
                for name in dir(module):
                    value: type[AnswerSource]= getattr(module, name)
                    if is_valid_obj(value, AnswerSource):
                        modules_to_return.append(create_instance(value))
    return modules_to_return


def is_valid_obj(obj: type, cls: type) -> bool:
    if obj == cls:
        return False
    try:
        if issubclass(obj, cls):
            return True
    except:
        return False
    return False


def create_instance(cls: type[T], **kwargs: Any) -> T:
    return cls(**kwargs)
