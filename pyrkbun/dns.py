"""Porkbun DNS API - Command-based approach with PyrkbunClient
"""
from dataclasses import dataclass
from typing import List, Optional
from .const import SUPPORTED_DNS_RECORD_TYPES
from .client import PyrkbunClient


@dataclass
class DnsRecord:
    """Represents a DNS record"""
    id: str
    name: str
    type: str
    content: str
    ttl: Optional[str] = None
    prio: Optional[str] = None
    notes: Optional[str] = None


@dataclass  
class DnsResponse:
    """Response from DNS operations"""
    records: List[DnsRecord]


class Dns:
    """DNS API wrapper around PyrkbunClient
    
    Provides command-based methods for DNS operations.
    """
    
    def __init__(self, client: PyrkbunClient):
        """Initialize DNS wrapper with a PyrkbunClient
        
        Args:
            client: PyrkbunClient instance for API calls
        """
        self.client = client
        self._api_path = '/dns'
    
    def _normalize_name(self, name: str, domain: str) -> str:
        """Normalize DNS record name by removing domain suffix if present
        
        Args:
            name: The record name (possibly FQDN)
            domain: The domain being managed
            
        Returns:
            The record name without domain suffix
        """
        if not name:
            return ''
        
        # Remove trailing dot if present (FQDN format)
        if name.endswith('.'):
            name = name[:-1]
            
        # If name ends with the domain, remove the domain suffix
        domain_suffix = f'.{domain}'
        if name.endswith(domain_suffix):
            return name[:-len(domain_suffix)]
        
        # If name is exactly the domain, return empty string (root record)
        if name == domain:
            return ''
            
        return name

    def get_records(self, 
                   domain: str,
                   record_type: Optional[str] = None,
                   name: Optional[str] = None,
                   record_id: Optional[str] = None) -> DnsResponse:
        """Get DNS records for a domain
        
        Args:
            domain: Domain name
            record_type: Type of DNS record (A, AAAA, MX, etc.)
            name: Record name (subdomain)
            record_id: Specific record ID
            
        Returns:
            DnsResponse with list of DnsRecord objects
            
        Example:
            >>> dns = Dns(client)
            >>> response = dns.get_records('example.com', record_type='A')
            >>> for record in response.records:
            ...     print(f"{record.name}: {record.content}")
        """
        if record_type and record_type not in SUPPORTED_DNS_RECORD_TYPES:
            raise ValueError(f"Unsupported DNS record type: {record_type}")

        # Build the appropriate API path based on provided parameters
        if record_id:
            path = f'{self._api_path}/retrieve/{domain}/{record_id}'
        elif name:
            path = f'{self._api_path}/retrieveByNameType/{domain}/{record_type}/{name}'
        elif record_type:
            path = f'{self._api_path}/retrieveByNameType/{domain}/{record_type}'
        else:
            path = f'{self._api_path}/retrieve/{domain}'

        response = self.client.api_post(path)
        
        # Check for successful response
        if response.get('status') != 'SUCCESS':
            status = response.get('status', 'UNKNOWN')
            message = response.get('message', '')
            error_msg = f"API request failed with status '{status}'"
            if message:
                error_msg += f": {message}"
            raise RuntimeError(error_msg)
        
        # Convert API response to DnsRecord objects
        records = []
        for record_data in response['records']:
            # Handle missing 'notes' field that API sometimes doesn't return
            if 'notes' not in record_data:
                record_data['notes'] = ''
                
            records.append(DnsRecord(
                id=str(record_data['id']),
                name=self._normalize_name(record_data['name'], domain),
                type=record_data['type'],
                content=record_data['content'],
                ttl=record_data.get('ttl'),
                prio=record_data.get('prio'),
                notes=record_data.get('notes')
            ))
        
        return DnsResponse(records=records)

    def create_record(self,
                     domain: str,
                     record_type: str,
                     content: str,
                     name: Optional[str] = None,
                     ttl: Optional[str] = None,
                     prio: Optional[str] = None,
                     notes: Optional[str] = None) -> DnsRecord:
        """Create a new DNS record
        
        Args:
            domain: Domain name
            record_type: Type of DNS record (required)
            content: Record content (required - IP address, etc.)
            name: Record name/subdomain (optional)
            ttl: Time to live in seconds (optional)
            prio: Priority for MX records (optional)
            notes: Optional notes (optional)
            
        Returns:
            DnsRecord object representing the created record
            
        Example:
            >>> dns = Dns(client)
            >>> record = dns.create_record('example.com', 'A', '1.2.3.4', name='www')
        """
        if record_type not in SUPPORTED_DNS_RECORD_TYPES:
            raise ValueError(f"Unsupported DNS record type: {record_type}")
        
        # Build payload with only provided values
        payload = {
            'type': record_type,
            'content': content
        }
        
        if name is not None:
            payload['name'] = name
        if ttl is not None:
            payload['ttl'] = ttl
        if prio is not None:
            payload['prio'] = prio
        if notes is not None:
            payload['notes'] = notes
        
        path = f'{self._api_path}/create/{domain}'
        response = self.client.api_post(path, payload)
        
        # Check for successful response
        if response.get('status') != 'SUCCESS':
            status = response.get('status', 'UNKNOWN')
            message = response.get('message', '')
            error_msg = f"API request failed with status '{status}'"
            if message:
                error_msg += f": {message}"
            raise RuntimeError(error_msg)
        
        # Return a DnsRecord object with the created record info
        return DnsRecord(
            id=str(response['id']),
            name=name or '',
            type=record_type,
            content=content,
            ttl=ttl,
            prio=prio,
            notes=notes
        )

    def delete_record(self,
                     domain: str,
                     record_type: Optional[str] = None,
                     name: Optional[str] = None,
                     record_id: Optional[str] = None) -> None:
        """Delete a DNS record
        
        Args:
            domain: Domain name
            record_type: Type of DNS record (required if not using record_id)
            name: Record name/subdomain (required if not using record_id)
            record_id: Specific record ID (alternative to record_type + name)
            
        Example:
            >>> dns = Dns(client)
            >>> dns.delete_record('example.com', record_type='A', name='www')
            >>> # OR
            >>> dns.delete_record('example.com', record_id='12345')
        """
        if record_type and record_type not in SUPPORTED_DNS_RECORD_TYPES:
            raise ValueError(f"Unsupported DNS record type: {record_type}")

        if not record_id and (not record_type or not name):
            raise ValueError("Must provide either record_id OR both record_type and name")

        if record_id:
            path = f'{self._api_path}/delete/{domain}/{record_id}'
        else:
            path = f'{self._api_path}/deleteByNameType/{domain}/{record_type}/{name}'
            
        response = self.client.api_post(path)
        
        # Check for successful response
        if response.get('status') != 'SUCCESS':
            status = response.get('status', 'UNKNOWN')
            message = response.get('message', '')
            error_msg = f"API request failed with status '{status}'"
            if message:
                error_msg += f": {message}"
            raise RuntimeError(error_msg)

    def edit_record(self,
                   domain: str,
                   record_id: Optional[str] = None,
                   record_type: Optional[str] = None,
                   name: Optional[str] = None,
                   content: Optional[str] = None,
                   ttl: Optional[str] = None,
                   prio: Optional[str] = None,
                   notes: Optional[str] = None) -> DnsRecord:
        """Edit an existing DNS record
        
        Args:
            domain: Domain name
            record_id: Specific record ID (alternative to record_type + name)
            record_type: Type of DNS record (required if not using record_id)
            name: Record name/subdomain (required if not using record_id)
            content: New record content (optional)
            ttl: New time to live in seconds (optional)
            prio: New priority (optional)
            notes: New notes (optional)
            
        Returns:
            DnsRecord object representing the updated record
            
        Example:
            >>> dns = Dns(client)
            >>> record = dns.edit_record('example.com', record_type='A', name='www', content='1.2.3.5')
            >>> # OR
            >>> record = dns.edit_record('example.com', record_id='12345', content='1.2.3.5')
        """
        if record_type and record_type not in SUPPORTED_DNS_RECORD_TYPES:
            raise ValueError(f"Unsupported DNS record type: {record_type}")

        if not record_id and (not record_type or not name):
            raise ValueError("Must provide either record_id OR both record_type and name")

        # Build payload with only provided values
        payload = {}
        if name is not None:
            payload['name'] = name
        if record_type is not None:
            payload['type'] = record_type
        if content is not None:
            payload['content'] = content
        if ttl is not None:
            payload['ttl'] = ttl
        if prio is not None:
            payload['prio'] = prio
        if notes is not None:
            payload['notes'] = notes

        if not payload:
            raise ValueError("Must provide at least one field to update")

        if record_id:
            path = f'{self._api_path}/edit/{domain}/{record_id}'
        else:
            path = f'{self._api_path}/editByNameType/{domain}/{record_type}/{name}'
            
        response = self.client.api_post(path, payload)
        
        # Check for successful response
        if response.get('status') != 'SUCCESS':
            status = response.get('status', 'UNKNOWN')
            message = response.get('message', '')
            error_msg = f"API request failed with status '{status}'"
            if message:
                error_msg += f": {message}"
            raise RuntimeError(error_msg)
        
        # Get the updated record to return accurate data
        if record_id:
            updated_records = self.get_records(domain, record_id=record_id)
        else:
            updated_records = self.get_records(domain, record_type=record_type, name=name)
            
        if updated_records.records:
            return updated_records.records[0]
        else:
            raise RuntimeError("Failed to retrieve updated record")