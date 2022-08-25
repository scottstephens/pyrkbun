"""Porkbun DNS API
"""
from dataclasses import dataclass, field

from .const import SUPPORTED_DNS_RECORD_TYPES
from .util import api_post

@dataclass
class Dns():
    '''Class representing a DNS record

    Args:
    domain: Domain that hosts the record
    name: Name of the record, excluding the domain
    record_type: Type of DNS record to be created
    content: Content of the record. For an A record this would be an IP
    ttl: DNS Time-to-Live in seconds. Minimum value of 600 seconds
    prio (optional): Record priority where supported. Defaults to '0'
    notes (optional): Information note to be displayed in web GUI
        defaults to empty string
    record_id (optional): Porkbun DNS record ID, will be auto populated
        when api is called for get, create and update operations
        defaults to an empty string

    Usage:
    The class can be instantiated with record details and methods are
    availabe to perfrom create, update and delete operations on the
    record represnted by the class details.
    Alternatively, a range of class methods are available to send API
    commands without the need to first instantiate the class.
    '''

    # Just the right number of instance attributes
    # pylint: disable=too-many-instance-attributes
    domain: str
    record_type: str
    content: str
    name: str = ''
    ttl: str = '600'
    prio: str = '0'
    notes: str = ''
    record_id: str = ''

    __api_path: str = field(default='/dns', init=False, repr=False)

    def __setattr__(self, name, value):
        if name == 'name':
            value: str = '' if value == self.domain \
                else value.removesuffix(f'.{self.domain}')
        elif name == 'record_type':
            assert value in SUPPORTED_DNS_RECORD_TYPES
        elif name == 'notes':
            # Porkbun are working on notes return, but now its returning null instead
            # of an empty string. This check simply ensures type consistency for this field
            value = '' if value is None else value
        elif name == 'prio':
            # For certain record types the API is returning null for priotiy instead of a value.
            # Ensuring type consistency by setting null values to string value zero -> '0'.
            value = '0' if value is None else value
        elif name == 'record_id':
            # When creating a record the ID value is returned as an int.
            # Ensuring value is always stored as a string for type safety
            value = str(value)
        super().__setattr__(name, value)

    @classmethod
    def __cls_creator_formatter(cls, domain, api_response) -> list['Dns']:
        """Format API response and create class instances
        """
        records =[]
        for record in api_response['records']:
            # The PorkBun API is not returning 'notes' with records
            # Checking for 'notes' in response keys and adding if needed
            # Have raised issue with Porkbun support team
            if 'notes' not in record.keys():
                record['notes'] = ''
            records.append(cls(domain,
                               record['type'],
                               record['content'],
                               record['name'],
                               record['ttl'],
                               record['prio'],
                               record['notes'],
                               record['id']))
        return records

    @classmethod
    def get_records(cls,
                   domain: str,
                   record_type: str = None,
                   name: str = None,
                   record_id: str = None) -> list['Dns']:
        """Get specific DNS records by ID or type and name

        Usage:
        Either provide the record name and type (r_type),
        or the record ID.

        Example 1, Get by record name and type:
        >>> x = pyrkbun.dns.get_record('example.com', 'A', 'www')
        >>> print(x)
        [Dns(domain='example.com', name='www', record_type='A',
        content='198.51.100.45', ttl='650', prio='0', notes='',
        record_id='253440859')]

        Example 2, Get by record name and type where multiple entries exist:
        >>> x = pyrkbun.dns.get_record('example.com', 'A', 'www')
        >>> print(x)
        [Dns(domain='example.com', name='www', record_type='A',
        content='198.51.100.45', ttl='650', prio='0', notes='',
        record_id='253440859'), Dns(domain='example.com', .... ]

        Example 3, Get by record ID:
        >>> x = pyrkbun.dns.get_record('example.com', record_id ='253440859')
        >>> print(x)
        [Dns(domain='example.com', name='www', record_type='A',
        content='198.51.100.45', ttl='650', prio='0', notes='',
        record_id='253440859')]

        Example 4, Get all records:
        >>> x = pyrkbun.dns.get_records('example.com')
        >>> print(x)
        [Dns(domain='example.com', name='www', record_type='A',
        content='198.51.100.45', ttl='650', prio='0', notes='',
        record_id='253440859'), Dns(domain='example.com', .... ]

        Example 5, Get all MX records:
        >>> x = pyrkbun.dns.get_records('example.com', 'MX')
        >>> print(x)
        [Dns(domain='example.com', name='example.com', record_type='MX',
        content='mail.example.com', ttl='650', prio='10', notes='',
        record_id='253440860'), Dns(domain='example.com', .... ]
        """
        if record_type:
            assert record_type in SUPPORTED_DNS_RECORD_TYPES

        if record_id or name:
            path = f'{cls.__api_path}/retrieve/{domain}/{record_id}' if record_id \
                else f'{cls.__api_path}/retrieveByNameType/{domain}/{record_type}/{name}'
        else:
            path = f'{cls.__api_path}/retrieveByNameType/{domain}/{record_type}' if record_type \
                else f'{cls.__api_path}/retrieve/{domain}'

        response = api_post(path)
        records = cls.__cls_creator_formatter(domain, response)
        return records

    @classmethod
    def create_record(cls,
                      domain: str,
                      record: dict) -> dict:
        """Create a new DNS record

        Usage:
        Provide domain and a formatted dict containing record content

        Example:
        >>> record = {'name': 'www',
                      'type': 'A',
                      'content': '198.51.100.45',
                      'ttl': '620',
                      'prio': '0',
                      'notes': 'Company website'}
        >>> x = pyrkbun.dns.create_record('example.com', record)
        >>> print(x)
        {'status': 'SUCCESS', 'id': 253475380}
        """
        path = f'{cls.__api_path}/create/{domain}/'
        response = api_post(path, record)
        return response

    @classmethod
    def delete_record(cls,
                      domain: str,
                      record_type: str = None,
                      name: str = None,
                      record_id: str = None) -> dict:
        """Delete a specific DNS record

        Usage:
        Either provide the record name and type (record_type),
        or the record ID.

        Example 1, Get by record name and type:
        >>> x = pyrkbun.dns.delete_record('example.com', 'A', 'www')
        >>> print(x)
        {'status': 'SUCCESS'}

        Example 2, Get by record ID:
        >>> x = pyrkbun.dns.delete_record('example.com', r_id ='253440859')
        >>> print(x)
        {'status': 'SUCCESS'}
        """
        if record_type:
            assert record_type in SUPPORTED_DNS_RECORD_TYPES

        path = f'{cls.__api_path}/delete/{domain}/{record_id}' if record_id \
            else f'{cls.__api_path}/deleteByNameType/{domain}/{record_type}/{name}'
        response = api_post(path)
        return response

    @classmethod
    def edit_record(cls,
                    domain: str,
                    updates: dict,
                    record_type: str = None,
                    name: str = None,
                    record_id: str = None) -> dict:
        """Edit a specific DNS record

        Usage:
        Provide domain and a formatted dict containing record content

        Example:
        >>> record = {'name': 'www',
                      'type': 'A',
                      'content': '198.51.100.45',
                      'ttl': '620',
                      'prio': '0',
                      'notes': 'Company website'}
        >>> x = pyrkbun.dns.create_record('example.com', record)
        >>> print(x)
        {'status': 'SUCCESS'}
        """
        if record_type:
            assert record_type in SUPPORTED_DNS_RECORD_TYPES

        path = f'{cls.__api_path}/edit/{domain}/{record_id}' if record_id \
            else f'{cls.__api_path}/editByNameType/{domain}/{record_type}/{name}'
        response = api_post(path, updates)
        return response

    def refresh(self) -> dict:
        """Refresh DNS class instance details from API
        """
        path = f'{self.__api_path}/retrieve/{self.domain}/{self.record_id}'
        response = api_post(path)
        record: dict = response['records'][0]
        if 'notes' not in record.keys():
            record['notes'] = ''
        self.name = record['name']
        self.record_type = record['type']
        self.content = record['content']
        self.ttl = record['ttl']
        self.prio = record['prio']
        self.notes = record['notes']
        self.record_id = record['id']
        return response

    def create(self) -> dict:
        """Create record based on class instance attributes
        """
        path = f'{self.__api_path}/create/{self.domain}'
        payload = {'name': self.name,
                   'type': self.record_type,
                   'content': self.content,
                   'ttl': self.ttl,
                   'prio': self.prio,
                   'notes': self.notes}
        response = api_post(path, payload)
        self.record_id = response['id']
        return response

    def update(self) -> dict:
        """Update record based on class instance attributes

        Note: Attempting an update without any valid changes to the DNS
        record will result in an API Error.
        """
        path = f'{self.__api_path}/edit/{self.domain}/{self.record_id}'
        payload = {'name': self.name,
                   'type': self.record_type,
                   'content': self.content,
                   'ttl': self.ttl,
                   'prio': self.prio,
                   'notes': self.notes}
        response = api_post(path, payload)
        return response

    def delete(self) -> dict:
        """Delete DNS record represented by class instance
        """
        path = f'{self.__api_path}/delete/{self.domain}/{self.record_id}'
        response = api_post(path)
        return response
