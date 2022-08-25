"""Constants utilsed throughout package modules

Attributes:
API_KEY: Porkbun API Key
API_SECRET_KEY: Porkbun API Secret Key
FORCE_V4: If this holds any value it forces the use of IPv4 for all API
    requests by selecting the Porkbun IPv4 only API base URL
VALID_HTTP_REPONSE: HTTP status codes indicating a sucessful API call
BASE_URL_V64: The default Porkbun API base URL supporting v4 and v6
BASE_URL_V4: Optional Porkbun API base URL supporting IPv4 only.
    If used, the API ping request will always return you IPv4 address
BASE_URL: Effective Base URL to be used for all API requests
"""
from os import getenv
from dotenv import load_dotenv

load_dotenv()

API_KEY: str = getenv('PYRK_API_KEY')
API_SECRET_KEY: str = getenv('PYRK_API_SECRET_KEY')
FORCE_V4: str = getenv('PYRK_FORCE_V4')

VALID_HTTP_RESPONSE: set = {200}

BASE_URL_V64: str = 'https://porkbun.com/api/json/v3'
BASE_URL_V4: str = 'https://api-ipv4.porkbun.com/api/json/v3'
BASE_URL: str = BASE_URL_V4 if FORCE_V4 else BASE_URL_V64

SUPPORTED_DNS_RECORD_TYPES = {'A',
                              'AAAA',
                              'MX',
                              'CNAME',
                              'ALIAS',
                              'TXT',
                              'NS',
                              'SRV',
                              'TLSA',
                              'CAA'}

class ApiError(Exception):
    """Porkbun REST API Error

    Attributes:
        http_status: HTTP status code returned from API
        status: Status message returned from API. Should always be 'Error'
        message: Error message returned from API explaing the error cause.
    """

    def __init__(self, http_status, status, message):
        super().__init__()
        self.http_status: int = http_status
        self.status: str = status
        self.message: str = message

    def __repr__(self) -> str:
        return f'ApiError({self.http_status}, {self.status}, {self.message})'
