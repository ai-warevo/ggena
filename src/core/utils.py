import importlib
import pkgutil
from src.core.registry import registry

def discover_and_register_generators(package_name: str):
    """
    Dynamically imports all subpackages in the given package to trigger 
    their self-registration in the GeneratorRegistry.
    """
    try:
        package = importlib.import_module(package_name)
    except ImportError as e:
        print(f"Error importing package {package_name}: {e}")
        return

    print(f"--- [Orchestrator] Discovering generators in '{package_name}' ---")
    for loader, module_name, is_pkg in pkgutil.iter_modules(package.__path__):
        full_module_name = f"{package_name}.{module_name}"
        print(f"  -> Loading {full_module_name}...")
        importlib.import_module(full_module_name)
