import os
from .openai_compatible import OpenAICompatibleProvider

def build_provider(provider_key: str):
    """
    Return (provider_instance, default_model) tuple for the given provider key.
    provider_key in { 'aliyun', 'openai', 'ollama', 'lmstudio' }
    """
    key = provider_key.lower()
    if key == "aliyun":
        base = os.getenv("ALIYUN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        api = os.getenv("ALIYUN_API_KEY", "")
        model = os.getenv("DEFAULT_MODEL", "qwen-turbo")
        return OpenAICompatibleProvider(base, api, "aliyun"), model
    if key == "openai":
        base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        api = os.getenv("OPENAI_API_KEY", "")
        model = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")
        return OpenAICompatibleProvider(base, api, "openai"), model
    if key == "ollama":
        base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        api = os.getenv("OLLAMA_API_KEY", "ollama")
        model = os.getenv("DEFAULT_MODEL", "qwen2:7b-instruct")
        return OpenAICompatibleProvider(base, api, "ollama"), model
    if key == "lmstudio":
        base = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
        api = os.getenv("LMSTUDIO_API_KEY", "lmstudio")
        model = os.getenv("DEFAULT_MODEL", "qwen2:7b-instruct")
        return OpenAICompatibleProvider(base, api, "lmstudio"), model

    # default fallback
    base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    api = os.getenv("OPENAI_API_KEY", "")
    model = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")
    return OpenAICompatibleProvider(base, api, "openai"), model
