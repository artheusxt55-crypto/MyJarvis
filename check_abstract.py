from openjarvis.engine._base import InferenceEngine

# Check abstract methods
for name in dir(InferenceEngine):
    attr = getattr(InferenceEngine, name, None)
    if hasattr(attr, '__isabstractmethod__') and attr.__isabstractmethod__:
        print(f'Abstract: {name}')
    elif isinstance(getattr(InferenceEngine, name, None), property) and hasattr(getattr(InferenceEngine, name), 'fget') and getattr(InferenceEngine, name).fget and getattr(InferenceEngine, name).fget.__isabstractmethod__:
        print(f'Abstract property: {name}')