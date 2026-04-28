from abc import ABC, abstractmethod


class LLM(ABC):
    model_name: str
    max_tokens: int
    temperature: float

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Generate text based on the provided prompt."""
        pass


import os
from google import genai
from google.genai import types
import anthropic
from openai import OpenAI


class GeminiLLM(LLM):
    def __init__(
        self, model_name: str, max_tokens: int = 1024, temperature: float = 0.0
    ):
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        # self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        self.api_key = os.getenv("GEMINI_API_KEY")
        print(
            f"GEMINI_API_KEY: {'*****'+self.api_key[-5:] if self.api_key else 'None'}"
        )

    # https://github.com/googleapis/python-genai/issues/626
    # set max_output_tokens to None temporarily due to a bug
    # TODO: remove when fixed
    def generate(self, prompt: str) -> str:
        client = genai.Client(api_key=self.api_key)
        try:
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    # max_output_tokens=self.max_tokens,
                    temperature=self.temperature
                ),
            )
        except Exception as error:
            print(f"Gemini API Error: {error}")
            return ""
        return response.text or ""


class GeminiCLILLM(LLM):
    def __init__(
        self, model_name: str, max_tokens: int = 1024, temperature: float = 0.0
    ):
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature

    def generate(self, prompt: str) -> str:
        import subprocess

        try:
            response = subprocess.run(
                ["gemini", "--prompt", prompt, "--model", self.model_name],
                check=True,
                capture_output=True,
                text=True,
            )
        except Exception as error:
            print(f"Gemini CLI Error: {error}")
            return ""
        return response.stdout or ""


class AnthropicLLM(LLM):
    def __init__(
        self, model_name="claude-opus-4-20250514", max_tokens=1024, temperature=0.0
    ):
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature

        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        print(
            f"ANTHROPIC_API_KEY: {'*****'+self.api_key[-5:] if self.api_key else 'None'}"
        )

    def generate(self, prompt: str) -> str:
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        try:
            response = client.messages.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            if response.type == "error":
                raise Exception(response)
        except Exception as error:
            print(f"Claude Error: {error}")
            return ""

        # the SDK returns a list of blocks of type "text" and "image"
        text_blocks = filter(lambda block: block.type == "text", response.content)
        return "\n\n".join(block.text for block in text_blocks)


class OpenAILLM(LLM):
    def __init__(
        self, model_name="gpt-4o-mini", base_url=None, max_tokens=1024, temperature=0.0
    ):
        self.name, self.max_tokens, self.temperature = (
            model_name,
            max_tokens,
            temperature,
        )
        self.base_url = base_url

    def generate(self, prompt: str) -> str:

        client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY", "DUMMY" if self.base_url else None),
            base_url=self.base_url,  # works for vLLM / Ollama too
        )

        try:
            resp = client.chat.completions.create(
                model=self.name,
                messages=[{"role": "user", "content": prompt}],
                # max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
        except Exception as error:
            print(f"Openai Error: {error}")
            return ""
        return resp.choices[0].message.content or ""


class DeepseekLLM(LLM):
    def __init__(
        self,
        model_name="deepseek/deepseek-r1:free",
        base_url="https://openrouter.ai/api/v1",
        max_tokens=1024,
        temperature=0.0,
    ):
        self.name, self.max_tokens, self.temperature = (
            model_name,
            max_tokens,
            temperature,
        )
        self.base_url = base_url

    def generate(self, prompt: str) -> str:

        client = OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY", "DUMMY" if self.base_url else None),
            base_url=self.base_url,  # works for vLLM / Ollama too
        )

        try:
            resp = client.chat.completions.create(
                model=self.name,
                messages=[{"role": "user", "content": prompt}],
                # max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
        except Exception as error:
            print(f"Deepseek (via OpenRouter) Error: {error}")
            return ""
        return resp.choices[0].message.content or ""


_PROVIDERS = {
    "gemini": GeminiLLM,
    "geminiCLI": GeminiCLILLM,
    "openai": OpenAILLM,
    "anthropic": AnthropicLLM,
    "deepseek": DeepseekLLM,
}


def get_llm(**kwargs) -> LLM:
    """
    Factory function to get an instance of a specific LLM.
    Currently supports Gemini, OpenAI, and Anthropic.
    """

    cls = _PROVIDERS.get(kwargs.get("provider"))
    if cls is None:
        raise ValueError(
            f"Unsupported LLM provider: {kwargs.get('provider')}. "
            "Currently only 'gemini' is supported."
        )

    return cls(
        model_name=kwargs.get("model_name"),
        max_tokens=kwargs.get("max_tokens", 1024),
        temperature=kwargs.get("temperature", 0.0),
    )
