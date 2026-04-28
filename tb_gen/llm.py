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
import json
from vllm import LLM, SamplingParams
import torch.distributed as dist
import torch


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
                seed=30,  # can change
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


class DeepseekLOCALLLM(LLM):
    def __init__(
        self,
        model_name="/mnt/shared/SINICA_NTU/model_weights/DeepSeek-R1-0528",
        # base_url="https://openrouter.ai/api/v1",
        max_tokens=1024,
        temperature=0.0,
    ):
        self.name, self.max_tokens, self.temperature = (
            model_name,
            max_tokens,
            temperature,
        )
        # self.base_url = base_url
        self.llm = LLM(
            model=model_name,
            tensor_parallel_size=8,
            pipeline_parallel_size=2,
            dtype="float16",
            distributed_executor_backend="external_launcher",
            trust_remote_code=True,
            max_num_seqs=256,
            max_model_len=self.max_tokens,
            # max_seq_len_to_capture=16384,
            # gpu_memory_utilization = 0.6,
            # enable_reasoning=True,
            # reasoning_parser="deepseek_r1",
            enforce_eager=True,
        )

    def generate(self, prompt: str) -> str:

        WORLD_RANK = int(os.environ.get("RANK", 0))

        sampling_params = SamplingParams(
            temperature=self.temperature, max_tokens=self.max_tokens
        )
        # generation = self.llm.generate(prompt, sampling_params)

        # if WORLD_RANK == 0:
        #     for i, org_i, gen in zip(range(len(prompt)), indices, generation):
        #         generated_text = gen.outputs[0].text
        #         dataset[org_i][out_key] = generated_text
        #         print("=" * 20)
        #         print(f"\n[{i}] PROMPT:\n")
        #         print(prompt[i])
        #         print(f"\n[{i}] RESPONSE:\n")
        #         print(generated_text)

        #     with open(input_path, "w") as f:
        #         json.dump({"dataset": dataset}, f, indent=4)
        # else:
        #     time.sleep(5)

        # dist.barrier()
        # if WORLD_RANK == 0:
        try:
            generation = self.llm.generate([prompt], sampling_params)
        except Exception as error:
            print(f"Deepseek (via local vllm) Error: {error}")
            return ""
        return generation[0].outputs[0].text if generation else ""


class OpenAILLMTaipeiONEServer(LLM):
    def __init__(
        self,
        model_name="gpt-4o-mini",
        base_url="http://localhost:8000/v1",
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
            api_key=os.getenv("OPENAI_API_KEY", "DUMMY" if self.base_url else None),
            base_url=self.base_url,
            timeout=1200,
        )

        try:
            # print("requesting...")
            resp = client.chat.completions.create(
                model=self.name,
                messages=[{"role": "user", "content": prompt}],
                # max_tokens=self.max_tokens,
                temperature=self.temperature,
                seed=30,  # can change
            )
        except Exception as error:
            print(f"Openai Error: {error}")
            return ""
        return resp.choices[0].message.content or ""


_PROVIDERS = {
    "gemini": GeminiLLM,
    "geminiCLI": GeminiCLILLM,
    "openai": OpenAILLM,
    "anthropic": AnthropicLLM,
    "deepseek": DeepseekLLM,
    "deepseeklocal": DeepseekLOCALLLM,
    "openai_local_server": OpenAILLMTaipeiONEServer,
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
