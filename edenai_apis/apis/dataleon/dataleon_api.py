from io import BufferedReader
from typing import Dict, Sequence
import requests

from edenai_apis.features import ProviderInterface, OcrInterface
from edenai_apis.features.ocr import (
    InvoiceParserDataClass,
    CustomerInformationInvoice,
    InfosInvoiceParserDataClass,
    LocaleInvoice,
    MerchantInformationInvoice,
    TaxesInvoice,
    ReceiptParserDataClass,
    CustomerInformation,
    InfosReceiptParserDataClass,
    Locale,
    MerchantInformation,
    Taxes,
)
from edenai_apis.loaders.data_loader import ProviderDataEnum
from edenai_apis.loaders.loaders import load_provider
from edenai_apis.utils.conversion import convert_string_to_number
from edenai_apis.utils.types import ResponseType
from edenai_apis.utils.exception import ProviderException


class DataleonApi(ProviderInterface, OcrInterface):
    provider_name = "dataleon"

    def __init__(self) -> None:
        self.api_settings = load_provider(ProviderDataEnum.KEY, self.provider_name)
        self.api_key = self.api_settings["key"]
        self.url_invoice = self.api_settings["invoice_parser"]["url"]
        self.url_receipt = self.api_settings["receipt_parser"]["url"]
        self.headers = {
            "Api-Key": self.api_key,
        }

    def _normalize_invoice_result(
        self, original_result: Dict
    ) -> Dict:
        fields = {
            "ID": "invoice_number",
            "CustomerName": "customer_name",
            "IssueDate": "date",
            "Subtotal": "subtotal",
            "Tax": "taxes",
            "Total": "invoice_total",
            "DueDate": "due_date",
            "VendorAddress": "merchant_address",
            "VendorName": "merchant_name",
            "TVANumber": "TVA_number",
            "SIREN": "siren",
            "SIRET": "siret",
            "CustomerAddress": "customer_address",
        }

        normalized_response = {
            "customer_information": {},
            "merchant_information": {},
        }

        entities = original_result["entities"]
        for entity in entities:
            field_name = fields.get(entity.get("name", None), entity["name"].lower())
            if field_name == "logo":
                continue
            field_value = entity.get("text", None)

            if field_name in ["customer_name", "customer_address"]:
                normalized_response["customer_information"][field_name] = field_value

            elif field_name in ["merchant_address", "merchant_name", "siret", "siren"]:
                normalized_response["merchant_information"][field_name] = field_value
            else:
                normalized_response[field_name] = field_value

        return normalized_response

    def ocr__invoice_parser(
        self, 
        file: str, 
        language: str,
        file_url: str= ""
    ) -> ResponseType[InvoiceParserDataClass]:

        file_= open(file, "rb")
        response = requests.post(
            url=self.url_invoice, headers=self.headers, files={"file": file_}
        )
        file_.close()
        
        if response.status_code !=200:
            raise ProviderException(response.content)
        
        original_response = response.json()
        normalized_response = self._normalize_invoice_result(original_response)

        taxes: Sequence[TaxesInvoice] = [
            TaxesInvoice(
                value=convert_string_to_number(normalized_response.get("taxes"), float)
            )
        ]

        invoice_parser = InfosInvoiceParserDataClass(
            merchant_information = MerchantInformationInvoice(
                merchant_name=normalized_response["merchant_information"].get(
                    "merchant_name"
                ),
                merchant_siret = normalized_response["merchant_information"].get("siret"),
                merchant_siren = normalized_response["merchant_information"].get("siren"),
                merchant_address = normalized_response["merchant_information"].get("merchant_address"),
            ),
            customer_information = CustomerInformationInvoice(
                customer_name = normalized_response["customer_information"].get("customer_name")
            ),
            invoice_number=normalized_response.get("invoice_number"),
            invoice_total=convert_string_to_number(
                normalized_response.get("invoice_total"), float
            ),
            invoice_subtotal=convert_string_to_number(
                normalized_response.get("subtotal"), float
            ),
            date=normalized_response.get("date"),
            due_date=normalized_response.get("due_date"),
            taxes=taxes,
            locale=LocaleInvoice(currency=normalized_response.get("currency")),
        )

        result = ResponseType[InvoiceParserDataClass](
            original_response=original_response,
            standardized_response=InvoiceParserDataClass(
                extracted_data=[invoice_parser]
            ),
        )
        return result

    def ocr__receipt_parser(
        self, 
        file: str, 
        language: str,
        file_url: str= ""
    ) -> ResponseType[ReceiptParserDataClass]:

        file_ = open(file, "rb")

        response = requests.post(
            url=self.url_receipt, headers=self.headers, files={"file": file_}
        )

        file_.close()
        
        if response.status_code !=200:
            raise ProviderException(response.content)
        
        original_response = response.json()
        normalized_response = self._normalize_invoice_result(original_response)

        taxes: Sequence[Taxes] = [
            Taxes(
                taxes=convert_string_to_number(normalized_response.get("taxes"), float)
            )
        ]
        ocr_receipt = InfosReceiptParserDataClass(
            invoice_number=normalized_response.get("invoice_number"),
            invoice_total=convert_string_to_number(
                normalized_response.get("invoice_total"), float
            ),
            invoice_subtotal=convert_string_to_number(
                normalized_response.get("subtotal"), float
            ),
            date=normalized_response.get("date"),
            due_date = normalized_response.get("due_date"),
            customer_information=CustomerInformation(
                customer_name=normalized_response["customer_information"].get(
                    "customer_name"
                ),
            ),
            merchant_information=MerchantInformation(
                merchant_name=normalized_response["merchant_information"].get(
                    "merchant_name"
                ),
                merchant_siret = normalized_response["merchant_information"].get("siret"),
                merchant_siren = normalized_response["merchant_information"].get("siren"),
                merchant_address = normalized_response["merchant_information"].get("merchant_address")
            ),
            taxes=taxes,
            locale=Locale(currency=normalized_response.get("currency")),
        )

        result = ResponseType[ReceiptParserDataClass](
            original_response=original_response,
            standardized_response=ReceiptParserDataClass(extracted_data=[ocr_receipt]),
        )
        return result
