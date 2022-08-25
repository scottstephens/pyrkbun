"""Porkbun SSL certificate API
"""
from .util import api_post

def get(domain):
    """Retrieve the SSL certificate bundle for the domain.
    
    Example:
    >>> import pyrkbun
    >>> response = pyrkbun.ssl.get('example.com')
    >>> print(response)
    {'status': 'SUCCESS',
    "intermediatecertificate": "<cert-data>",
	"certificatechain": "<cert-data>",
	"privatekey": "<cert-data>",
	"publickey": "<cert-data>"}
    """
    path = f'/ssl/retrieve/{domain}'
    response = api_post(path)
    return response
