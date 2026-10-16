import importlib
import pkgutil
import logging
from src.core.registry import GeneratorRegistry

logger = logging.getLogger(__name__)

def discover_and_register_generators(package_name: str, registry: GeneratorRegistry):
    """
    Dynamically imports all subpackages in the given package to trigger 
    their self-registration in the GeneratorRegistry.
    """
    try:
        package = importlib.import_module(package_name)
    except ImportError as e:
        logger.error(f"Error importing package {package_name}: {e}")
        return

    logger.info(f"--- [Orchestrator] Discovering generators in '{package_name}' ---")
    for loader, module_name, is_pkg in pkgutil.iter_modules(package.__path__):
        full_module_name = f"{package_name}.{module_name}"
        logger.debug(f"  -> Loading {full_module_name}...")
        importlib.import_module(full_module_name)
