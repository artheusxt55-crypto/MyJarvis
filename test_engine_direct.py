from myjarvis.core.config import load_config
config = load_config()

from myjarvis.engine.custom_openai import CustomOpenAIEngine
engine = CustomOpenAIEngine(config)
print('Engine created:', engine)
print('Base URL:', engine.base_url)
print('API Key set:', bool(engine.api_key))
print('Provider:', engine.provider)