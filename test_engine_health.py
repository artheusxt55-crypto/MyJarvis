from myjarvis.core.config import load_config
config = load_config()

from openjarvis.engine._discovery import _make_engine
from openjarvis.core.registry import EngineRegistry

print('Registry contains nvidia-openai:', EngineRegistry.contains('nvidia-openai'))
print('Engine class:', EngineRegistry.get('nvidia-openai'))

engine = _make_engine('nvidia-openai', config)
print('Engine created:', engine)
print('Engine health:', engine.health())