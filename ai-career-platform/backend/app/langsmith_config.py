import os

from app.config import settings

# Only enable LangSmith tracing when explicitly on and a key is set
if settings.LANGCHAIN_TRACING_V2 and settings.LANGCHAIN_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT
else:
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
