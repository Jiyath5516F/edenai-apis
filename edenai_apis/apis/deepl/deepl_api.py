import requests
from edenai_apis.features.provider.provider_interface import ProviderInterface
from edenai_apis.features.translation.automatic_translation import AutomaticTranslationDataClass
from edenai_apis.features.translation.translation_interface import TranslationInterface
from edenai_apis.loaders.data_loader import ProviderDataEnum
from edenai_apis.utils.exception import ProviderException
from edenai_apis.loaders.loaders import load_provider
from edenai_apis.utils.types import ResponseType


class DeeplApi(ProviderInterface, TranslationInterface):
    provider_name = "deepl"
    base_url = "https://api.deepl.com/v2/"

    def __init__(self) -> None:
        self.api_settings = load_provider(ProviderDataEnum.KEY, self.provider_name)
        self.api_key = self.api_settings["api_key"]
        self.header = {
            "authorization": f"DeepL-Auth-Key {self.api_key}",
        }

    def translation__automatic_translation(
        self, source_language: str, target_language: str, text: str
    ) -> ResponseType[AutomaticTranslationDataClass]:
        url = f"{self.base_url}translate"

        data = {
            "text": text,
            "source_lang": source_language,
            "target_lang": target_language,
        }

        response = requests.request("POST", url, headers=self.header, data=data)
        original_response = response.json()

        if response.status_code != 200:
            raise ProviderException(message=original_response['message'], code=response.status_code)


        standardized_response = AutomaticTranslationDataClass(
            text=original_response['translations'][0]['text']
        )

        return ResponseType[AutomaticTranslationDataClass](
            original_response=original_response, standardized_response=standardized_response
        )
