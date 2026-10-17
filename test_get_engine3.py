from myjarvis.core.config import load_config
config = load_config()

from openjarvis.engine._discovery import get_engine, _make_engine
from openjarvis.core.registry import EngineRegistry

print('Registry contains nvidia-openai:', EngineRegistry.contains('nvidia-openai'))

factory = EngineRegistry.get('nvidia-openai')
engine = factory(config)
print('Engine created:', engine)
print('Engine health:', engine.health())

# Test get_engine
print('\nTesting get_engine...')
result = get_engine(config, 'nvidia-openai')
print('Result:', result)

# Check what _make_engine returns
engine2 = _make_engine('nvidia-openai', config)
print('_make_engine result:', engine2)
print('Engine2 health:', engine2.health() if engine2 else 'None')

# Check can_serve
if engine2:
    print('can_serve:', engine2.can_serve(config.intelligence.default_model))