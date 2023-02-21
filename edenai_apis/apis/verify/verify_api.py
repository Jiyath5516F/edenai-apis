from http import HTTPStatus
from io import BufferedReader
import mimetypes
import uuid

import requests
from edenai_apis.features.ocr.ocr_interface import OcrInterface
from edenai_apis.features.ocr.invoice_parser.invoice_parser_dataclass import (
    BankInvoice,
    CustomerInformationInvoice,
    InfosInvoiceParserDataClass,
    InvoiceParserDataClass,
    ItemLinesInvoice,
    LocaleInvoice,
    MerchantInformationInvoice,
    TaxesInvoice,
)
from edenai_apis.features.ocr.receipt_parser.receipt_parser_dataclass import (
    CustomerInformation,
    Locale,
    InfosReceiptParserDataClass,
    ItemLines,
    MerchantInformation,
    PaymentInformation,
    ReceiptParserDataClass,
    Taxes
)
from edenai_apis.features.provider.provider_interface import ProviderInterface
from edenai_apis.loaders.data_loader import load_key
from edenai_apis.utils.types import ResponseType
from edenai_apis.utils.exception import ProviderException


class VerifyApi(ProviderInterface, OcrInterface):
    provider_name = "verify"

    def __init__(self):
        self.api_settings = load_key(provider_name=self.provider_name)
        self.client_id = self.api_settings["client_id"]
        self.client_secret = self.api_settings["client_secret"]
        self.authorization = self.api_settings["Authorization"]
        self.url = self.api_settings["endpoint_url"]

        self.headers = {
            "Accept": "application/json",
            "CLIENT-ID": self.client_id,
            "Authorization": self.authorization,
        }

    def _make_post_request(self, file: BufferedReader):
        payload = {
            "file_name": f"test-{uuid.uuid4()}"
        }

        files = {
            "file": ('file', file, mimetypes.guess_type(file.name)[0])
        }

        response = requests.request(
            method="POST",
            url=self.url + '/documents',
            headers=self.headers,
            data=payload,
            files=files
        )

        if response.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
            raise ProviderException(message=response.json(), code=response.status_code)

        if response.status_code != HTTPStatus.CREATED:
            raise ProviderException(message=response.json(), code=response.status_code)

        return response.json()


    def ocr__invoice_parser(self, file: BufferedReader, language: str) -> ResponseType[InvoiceParserDataClass]:
        original_response = self._make_post_request(file)

        ship_name = original_response['ship_to']['name']
        ship_address = original_response['ship_to']['address']
        if ship_name is not None and ship_address is not None:
            ship_address = ship_name + ship_address

        customer_information = CustomerInformationInvoice(
            customer_name=original_response['bill_to']['name'],
            customer_address=original_response['bill_to']['address'],
            customer_tax_id=original_response['bill_to']['vat_number'],
            customer_id=original_response['account_number'],
            customer_billing_address=original_response['bill_to']['address'],
            customer_shipping_address=ship_address,
        )

        merchant_information = MerchantInformationInvoice(
            merchant_name=original_response['vendor']['name'],
            merchant_address=original_response['vendor']['address'],
            merchant_phone=original_response['vendor']['phone_number'],
            merchant_email=original_response['vendor']['email'],
            merchant_tax_id=original_response['vendor']['vat_number'],
            merchant_id=original_response['vendor']['reg_number'],
            merchant_website=original_response['vendor']['web'],
            merchant_fax=original_response['vendor']['fax_number'],
        )

        bank_informations = BankInvoice(
            account_number=original_response['vendor']['account_number'],
            iban=original_response['vendor']['iban'],
            swift=original_response['vendor']['bank_swift'],
            vat_number=original_response['vendor']['vat_number'],
        )

        item_lines = []
        for item in original_response['line_items']:
            item_lines.append(ItemLinesInvoice(
                description=item['description'],
                quantity=item['quantity'],
                discount=item['discount'],
                unit_price=item['price'],
                tax_item=item['tax'],
                tax_rate=item['tax_rate'],
                amount=item['total'],
                date_item=item['date'],
                product_code=item['sku'],
            ))

        info_invoice = [InfosInvoiceParserDataClass(
            customer_information=customer_information,
            merchant_information=merchant_information,
            taxes=[TaxesInvoice(value=original_response['tax'])],
            invoice_total=original_response['total'],
            invoice_subtotal=original_response['subtotal'],
            invoice_number=original_response['invoice_number'],
            date=original_response['updated_date'],
            purchase_order=original_response['purchase_order_number'],
            item_lines=item_lines,
            locale=LocaleInvoice(currency=original_response['currency_code']),
            bank_informations=bank_informations,
        )]

        standardized_response = InvoiceParserDataClass(extracted_data=info_invoice)

        return ResponseType[InvoiceParserDataClass](
            original_response=original_response,
            standardized_response=standardized_response
        )

    def ocr__receipt_parser(self, file: BufferedReader, language: str) -> ResponseType[ReceiptParserDataClass]:
        original_response = self._make_post_request(file)

        customer_information = CustomerInformation(
            customer_name=original_response['bill_to']['name'],
        )

        merchant_information = MerchantInformation(
            merchant_name=original_response['vendor']['name'],
            merchant_address=original_response['vendor']['address'],
            merchant_phone=original_response['vendor']['phone_number'],
            merchant_url=original_response['vendor']['web'],
        )

        payment_information = PaymentInformation(
            card_type=original_response['payment']['type'],
            card_number=original_response['payment']['card_number'],
        )

        items_lines = []
        for item in original_response['line_items']:
            items_lines.append(ItemLines(
                description=item['description'],
                quantity=item['quantity'],
                unit_price=item['price'],
                amount=item['total'],
            ))

        info_receipt = [InfosReceiptParserDataClass(
            customer_information=customer_information,
            merchant_information=merchant_information,
            payment_information=payment_information,
            invoice_number=original_response['invoice_number'],
            invoice_subtotal=original_response['subtotal'],
            invoice_total=original_response['total'],
            date=original_response['updated_date'],
            item_lines=items_lines,
            locale=Locale(currency=original_response['currency_code']),
            taxes=[Taxes(value=original_response['tax'])],
            category=original_response['category'],
        )]

        standardized_response = ReceiptParserDataClass(extracted_data=info_receipt)

        return ResponseType[ReceiptParserDataClass](
            original_response=original_response,
            standardized_response=standardized_response
        )
