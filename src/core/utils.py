import importlib
import pkgutil
import logging
from src.core.registry import GeneratorRegistry
from src.generators.base import BaseGenerator

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
    
    for module_info in pkgutil.walk_packages(package.__path__, prefix=f"{package_name}."):
        logger.info(f"  -> Loading {module_info.name}...")
        try:
            importlib.import_module(module_info.name)
        except Exception as e:
            logger.error(f"Failed to load module {module_info.name}: {e}")

    def get_all_subclasses(cls):
        subclasses = set(cls.__subclasses__())
        return subclasses.union([s for c in subclasses for s in get_all_subclasses(c)])

    all_generator_classes = get_all_subclasses(BaseGenerator)
    
    for gen_cls in all_generator_classes:
        if gen_cls == BaseGenerator:
            continue
            
        names = getattr(gen_cls, "aliases", [gen_cls.__name__.lower().replace("generator", "")])
        
        for name in names:
            logger.info(f"   [Registry] Auto-registered: {name} -> {gen_cls.__name__}")
            registry.register(name, gen_cls)