"""Porkbun domain pricing API - Command-based approach with PyrkbunClient
"""
from dataclasses import dataclass
from typing import Dict, Optional
from dacite import from_dict
from .client import PyrkbunClient


@dataclass
class Coupon:
    """Represents a domain pricing coupon"""
    code: str
    max_per_user: int
    first_year_only: str
    type: str
    amount: int


@dataclass
class TldPricing:
    """Represents pricing for a specific TLD"""
    registration: str
    renewal: str
    transfer: str
    coupons: Optional[list[Coupon]] = None


@dataclass
class PricingResponse:
    """Response from pricing operations"""
    pricing: Dict[str, TldPricing]


class Pricing:
    """Pricing API wrapper around PyrkbunClient
    
    Provides command-based methods for pricing operations.
    """
    
    def __init__(self, client: PyrkbunClient):
        """Initialize Pricing wrapper with a PyrkbunClient
        
        Args:
            client: PyrkbunClient instance for API calls
        """
        self.client = client

    def get(self) -> PricingResponse:
        """Check default domain pricing information for all supported TLDs

        Returns:
            PricingResponse with pricing information for all TLDs

        Example:
            >>> pricing = Pricing(client)
            >>> response = pricing.get()
            >>> for tld, price_info in response.pricing.items():
            ...     print(f"{tld}: registration ${price_info.registration}")
        """
        path = '/pricing/get'
        response = self.client.api_post(path, auth=False)
        
        # Check for successful response
        if response.get('status') != 'SUCCESS':
            status = response.get('status', 'UNKNOWN')
            message = response.get('message', '')
            error_msg = f"API request failed with status '{status}'"
            if message:
                error_msg += f": {message}"
            raise RuntimeError(error_msg)
        
        # Convert API response to structured objects using dacite
        pricing = from_dict(PricingResponse, response)
        return pricing
