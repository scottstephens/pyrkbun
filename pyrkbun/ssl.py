"""Porkbun SSL certificate API - Command-based approach with PyrkbunClient
"""
from dataclasses import dataclass
from .client import PyrkbunClient


@dataclass
class SslCertificate:
    """Represents an SSL certificate bundle"""
    intermediatecertificate: str
    certificatechain: str
    privatekey: str
    publickey: str


class Ssl:
    """SSL API wrapper around PyrkbunClient
    
    Provides command-based methods for SSL operations.
    """
    
    def __init__(self, client: PyrkbunClient):
        """Initialize SSL wrapper with a PyrkbunClient
        
        Args:
            client: PyrkbunClient instance for API calls
        """
        self.client = client

    def get(self, domain: str) -> SslCertificate:
        """Retrieve the SSL certificate bundle for the domain.
        
        Args:
            domain: Domain name to retrieve SSL certificate for
            
        Returns:
            SslCertificate with certificate bundle data
    
        Example:
            >>> ssl = Ssl(client)
            >>> cert = ssl.get('example.com')
            >>> print(f"Private key length: {len(cert.privatekey)}")
        """
        path = f'/ssl/retrieve/{domain}'
        response = self.client.api_post(path)
        
        # Check for successful response
        if response.get('status') != 'SUCCESS':
            status = response.get('status', 'UNKNOWN')
            message = response.get('message', '')
            error_msg = f"API request failed with status '{status}'"
            if message:
                error_msg += f": {message}"
            raise RuntimeError(error_msg)
        
        return SslCertificate(
            intermediatecertificate=response['intermediatecertificate'],
            certificatechain=response['certificatechain'],
            privatekey=response['privatekey'],
            publickey=response['publickey']
        )