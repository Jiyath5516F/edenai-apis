from io import BufferedReader
from time import sleep
from typing import Sequence
import uuid

import requests
from azure.storage.blob import BlobServiceClient

from edenai_apis.features.translation import (
    AutomaticTranslationDataClass,
    InfosLanguageDetectionDataClass,
    LanguageDetectionDataClass,
)
from edenai_apis.features.translation.document_translation.document_translation_dataclass import DocumentTranslationDataClass
from edenai_apis.features.translation.translation_interface import TranslationInterface
from edenai_apis.utils.conversion import format_string_url_language
from edenai_apis.utils.exception import ProviderException
from edenai_apis.utils.languages import get_language_name_from_code
from edenai_apis.utils.types import ResponseType


class MicrosoftTranslationApi(TranslationInterface):
    def translation__language_detection(
        self, text
    ) -> ResponseType[LanguageDetectionDataClass]:
        response = requests.post(
            url=f"{self.url['text']}",
            headers=self.headers["text"],
            json={
                "kind": "LanguageDetection",
                "parameters": {"modelVersion": "latest"},
                "analysisInput": {"documents": [{"id": "1", "text": text}]},
            },
        )

        data = response.json()
        if response.status_code != 200:
            raise ProviderException(
                message=data["error"]["message"], code=response.status_code
            )

        items: Sequence[InfosLanguageDetectionDataClass] = []
        for lang in data["results"]["documents"]:
            items.append(
                InfosLanguageDetectionDataClass(
                    language=lang["detectedLanguage"]["iso6391Name"],
                    display_name=get_language_name_from_code(
                        isocode=lang["detectedLanguage"]["iso6391Name"]
                    ),
                    confidence=lang["detectedLanguage"]["confidenceScore"],
                )
            )
        return ResponseType[LanguageDetectionDataClass](
            original_response=data,
            standardized_response=LanguageDetectionDataClass(items=items),
        )

    def translation__automatic_translation(
        self, source_language: str, target_language: str, text: str
    ) -> ResponseType[AutomaticTranslationDataClass]:
        """
        :param source_language:    String that contains language name of origin text
        :param target_language:    String that contains language name of origin text
        :param text:        String that contains input text to translate
        :return:            String that contains output result
        """

        # Create configuration dictionnary

        url = format_string_url_language(
            self.url["translator"], source_language, "from", self.provider_name
        )
        url = format_string_url_language(url, target_language, "to", self.provider_name)

        body = [
            {
                "text": text,
            }
        ]
        # Getting response of API
        response = requests.post(url, headers=self.headers["translator"], json=body)
        data = response.json()

        # Create output TextAutomaticTranslation object
        standardized_response = AutomaticTranslationDataClass(
            text=data[0]["translations"][0]["text"]
        )

        return ResponseType[AutomaticTranslationDataClass](
            original_response=data, standardized_response=standardized_response
        )

    def translation__document_translation(
        self,
        file: BufferedReader,
        source_language: str,
        target_language: str,
    ) -> ResponseType[DocumentTranslationDataClass]:
        account_url = self.api_settings["translator"]["url_storage"]

        blob_service_client = BlobServiceClient(account_url)

        local_file_name = str(uuid.uuid4()) + ".pdf"
        blob_client = blob_service_client.get_blob_client(container='source', blob=local_file_name)
        blob_client.upload_blob(file)

        sourceSASUrl = self.api_settings['translator']['source_storage']
        targetSASUrl = self.api_settings['translator']['target_storage']

        body = {
            "inputs": [
                {
                    "source": {
                        "sourceUrl": sourceSASUrl,
                        "storageSource": "AzureBlob",
                        "language": source_language
                    },
                    "targets": [
                        {
                            "targetUrl": targetSASUrl,
                            "storageSource": "AzureBlob",
                            "language": target_language
                        }
                    ]
                }
            ]
        }

        headers = {
          'Ocp-Apim-Subscription-Key': self.api_settings["translator"]['subscription_key'],
          'Content-Type': 'application/json',
        }

        response = requests.post('https://aicompare-translate.cognitiveservices.azure.com/translator/text/batch/v1.0/batches', headers=headers, json=body)

        if response.status_code != 202:
            raise ProviderException(message=response.reason, code=response.status_code)

        print(f"Response status code: {response.status_code} with reason: {response.reason}")
        print(f"Job ID: {response.headers['Operation-Location'].split('/')[-1]}")

        # i = 0
        # while i < 60:
        #     sleep(1)
        #     i += 1
        #     print("\rpending ...\testimated time: %d seconds" % (60 - i), end="")

        # blob_list = target_container_client.list_blobs()
        # for blob in blob_list:
        #     print("\t" + blob.name)

        containers = blob_service_client.list_containers()
        for container in containers:
            print(container.name)
            blobs = blob_service_client.get_container_client(container.name).list_blobs()
            for blob in blobs:
                print("\t" + blob.name)
                blob_service_client.get_blob_client(container.name, blob.name).delete_blob(delete_snapshots="include")
