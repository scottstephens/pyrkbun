"""Porkbun domain pricing API
"""
from .util import api_post

def get() -> dict:
    """Check default domain pricing information for all supported TLDs

    Example:
    >>> import pyrkbun
    >>> response = pyrkbun.pricing.get()
    >>> print(response)
    {'status': 'SUCCESS',
    'pricing': {'de': {'registration': '5.55', 'renewal': '4.11',
    'transfer': '4.11', 'coupons': {'registration':
    {'code': 'AWESOMENESS', 'max_per_user': 1, 'first_year_only': 'yes',
    'type': 'amount', 'amount': 1}}},
    'xof': {'registration': '6.49', 'renewal': '21.94', ... }
    """
    path = '/pricing/get'
    response = api_post(path, auth=False)
    return response
