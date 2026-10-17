from myjarvis.core.config import load_config
config = load_config()
print('Config intelligence.preferred_engine:', config.intelligence.preferred_engine)
print('Config intelligence.default_model:', config.intelligence.default_model)
print('Config intelligence.engine_config:', getattr(config, 'myjarvis_engine_config', None))

from openjarvis.engine._discovery import get_engine
result = get_engine(config, 'nvidia-openai')
print('Result:', result)
if result:
    key, engine = result
    print('Engine:', engine)
else:
    print('Engine not found')
    from openjarvis.core.registry import EngineRegistry
    print('Available:', list(EngineRegistry.keys()))