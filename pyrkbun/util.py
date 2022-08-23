"""Utilities
"""
import httpx
from .const import ApiError
from .const import API_KEY, API_SECRET_KEY, BASE_URL, VALID_HTTP_RESPONSE

def api_post(path: str, payload: dict = None, auth: bool = True) -> dict:
    """Format request and post to API endpoint

    Used by package modules to condoliate logic for API calls.

    Args:
    path: Section of API path that extends base URL
        (e.g. /dns/create/<domain>).
    payload (optional): JSON payload for API request formatted as dict.
        Payload will automatically be updated with API keys.
        Defaults to empty dict
    auth (optional): Does the API request require authentication.
        Defaults to True which atuo updates payload with auth data

    Rasies:
    ApiError(): If the API returns a non-200 status code an error will be
        raised encapsulating the error message and http status-code
    """
    payload = {} if payload is None else payload
    if auth:
        payload.update({'secretapikey': API_SECRET_KEY,'apikey': API_KEY})
    headers = {'content-type': 'application/json'}
    http_client = httpx.Client(http2=True, base_url=BASE_URL, headers=headers)
    with http_client as http_client:
        response = http_client.post(path, json=payload)
    result: dict = response.json()

    # pylint: disable=no-else-return
    if response.status_code in VALID_HTTP_RESPONSE:
        return result
    else:
        result.update({'http_status': response.status_code})
        raise ApiError(**result)

def api_ping() -> dict:
    """Basic request to poll API host and return your own IP

    Example:
        >>> import pyrkbun
        >>> response = pyrkbun.ping()
        >>> print(response)
        {'status': 'SUCCESS', 'yourIp': '198.51.100.45'}
    """
    path = '/ping'
    response = api_post(path)
    return response
