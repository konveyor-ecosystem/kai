from genai import Client, Credentials
from genai.extensions.langchain.chat_llm import LangChainChatInterface
from genai.schema import DecodingMethod
from langchain_community.chat_models import BedrockChat, ChatOllama, ChatOpenAI
from langchain_community.chat_models.fake import FakeListChatModel
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic.v1.utils import deep_update

from kai.models.kai_config import KaiConfigModels


class ModelProvider:
    def __init__(self, config: KaiConfigModels):
        self.llm_retries: int = config.llm_retries
        self.llm_retry_delay: float = config.llm_retry_delay

        model_class: BaseChatModel
        defaults: dict
        model_args: dict
        model_id: str

        # Set the model class, model args, and model id based on the provider
        match config.provider:
            case "ChatOllama":
                model_class = ChatOllama

                defaults = {
                    "model": "mistral",
                    "temperature": 0.1,
                    "max_tokens": None,
                    "streaming": True,
                }

                model_args = deep_update(defaults, config.args)
                model_id = model_args["model"]

            case "ChatOpenAI":
                model_class = ChatOpenAI

                defaults = {
                    "model": "gpt-3.5-turbo",
                    "temperature": 0.1,
                    # "model_kwargs": {
                    #     "max_tokens": None,
                    # },
                    "streaming": True,
                }

                model_args = deep_update(defaults, config.args)
                model_id = model_args["model"]

            case "ChatIBMGenAI":
                model_class = LangChainChatInterface

                defaults = {
                    "client": Client(credentials=Credentials.from_env()),
                    "model_id": "ibm-mistralai/mixtral-8x7b-instruct-v01-q",
                    "parameters": {
                        "decoding_method": DecodingMethod.SAMPLE,
                        # NOTE: probably have to do some more clever stuff regarding
                        # config. max_new_tokens and such varies between models
                        "max_new_tokens": 4096,
                        "min_new_tokens": 10,
                        "temperature": 0.05,
                        "top_k": 20,
                        "top_p": 0.9,
                        "return_options": {"input_text": False, "input_tokens": True},
                    },
                    "moderations": {
                        # Threshold is set to very low level to flag everything
                        # (testing purposes) or set to True to enable HAP with
                        # default settings
                        "hap": {"input": True, "output": False, "threshold": 0.01}
                    },
                    "streaming": True,
                }

                model_args = deep_update(defaults, config.args)
                model_id = model_args["model_id"]

            case "ChatBedrock":
                model_class = BedrockChat

                defaults = {
                    "model_id": "anthropic.claude-3-5-sonnet-20240620-v1:0",
                }

                model_args = deep_update(defaults, config.args)
                model_id = model_args["model_id"]

            case "FakeListChatModel":
                model_class = FakeListChatModel

                defaults = {
                    "responses": ["Default LLM response."],
                    "sleep": None,
                }

                model_args = deep_update(defaults, config.args)
                model_id = "fake-list-chat-model"

            case _:
                raise Exception(f"Unrecognized provider '{config.provider}'")

        self.provider_id: str = config.provider
        self.llm: BaseChatModel = model_class(**model_args)
        self.model_id: str = model_id

        if config.template is None:
            self.template = self.model_id
        else:
            self.template = config.template

        if config.llama_header is None:
            self.llama_header = self.model_id in [
                "mistralai/mistral-7b-instruct-v0-2",
                "mistralai/mixtral-8x7b-instruct-v01",
                "codellama/codellama-34b-instruct",
                "codellama/codellama-70b-instruct",
                "deepseek-ai/deepseek-coder-33b-instruct",
                "tiiuae/falcon-180b",
                "tiiuae/falcon-40b",
                "ibm/falcon-40b-8lang-instruct",
                "meta-llama/llama-2-70b-chat",
                "meta-llama/llama-2-13b-chat",
                "meta-llama/llama-2-7b",
                "meta-llama/llama-3-70b-instruct",
                "meta-llama/llama-3-8b-instruct",
            ]
        else:
            self.llama_header = config.llama_header
