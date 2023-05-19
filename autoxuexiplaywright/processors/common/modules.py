from sys import modules
from importlib.util import spec_from_file_location, module_from_spec
# Relative imports
from ...sdk import Module


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
                value = getattr(module, name)
                if (value != Module) and issubclass(value, Module):
                    try:
                        instance = value()
                    except:
                        pass
                    else:
                        if instance not in modules_to_return:
                            instance.start()
                            modules_to_return.append(instance)
    return modules_to_return
