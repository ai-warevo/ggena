from .image_generator import ImageGenerator
from .text_expander import translate_user_intent_to_tags
from src.core.registry import registry

# Register the generator
registry.register("image", ImageGenerator)
