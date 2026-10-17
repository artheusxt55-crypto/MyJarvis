from myjarvis.core.config import load_config
config = load_config()
print('Config intelligence:', config.intelligence)
print('Config intelligence.engine_config:', getattr(config.intelligence, 'engine_config', None))
print('Config intelligence.default_model:', config.intelligence.default_model)
print('Config intelligence.preferred_engine:', config.intelligence.preferred_engine)