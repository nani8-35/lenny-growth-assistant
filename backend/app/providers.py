"""A single streaming interface to the restricted Pi agent's local/cloud drivers."""
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
import json
import httpx
from .config import settings

class LLMProviderInterface(ABC):
    @abstractmethod
    async def stream(self, payload: dict) -> AsyncIterator[dict]:
        yield {}

class PiProvider(LLMProviderInterface):
    provider: str
    async def stream(self, payload: dict) -> AsyncIterator[dict]:
        async with httpx.AsyncClient(timeout=httpx.Timeout(settings().model_timeout,connect=10)) as client:
            async with client.stream('POST',settings().agent_url+'/generate',json={**payload,'provider':self.provider}) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line: yield json.loads(line)

class OllamaProvider(PiProvider):
    provider='ollama'

class AnthropicProvider(PiProvider):
    provider='anthropic'

def get_provider(name: str) -> LLMProviderInterface:
    if name=='ollama':return OllamaProvider()
    if name=='anthropic':return AnthropicProvider()
    raise ValueError('Unknown provider')
