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
    r_type: Type of DNS record to be created
    content: Content of the record. For an A record this would be an IP
    ttl: DNS Time-to-Live in seconds. Minimum value of 600 seconds
    prio (optional): Record priority where supported. Defaults to '0'
    notes (optional): Information note to be displayed in web GUI
        defaults to empty string
    r_id (optional): Porkbun DNS record ID, will be auto populated when
        api is called for get, create and update operations defaults to
        an empty string
    state (dont touch): Indicates wether record has been modified since
        retrieving from the API. 'SYNC', 'NOT_SYNC', 'DELETED'
    '''

    # Just the right number of instance attributes
    # pylint: disable=too-many-instance-attributes
    domain: str
    name: str
    r_type: str
    content: str
    ttl: str = '600'
    prio: str = '0'
    notes: str = ''
    r_id: str = ''
    state: str = field(default='NOT_SYNC', repr=False)

    _name: str = field(init=False, repr=False)
    _r_type: str = field(init=False, repr=False)
    _content: str = field(init=False, repr=False)
    _ttl: str = field(init=False, repr=False)
    _prio: str = field(init=False, repr=False)
    _notes: str = field(init=False, repr=False)

    __api_path: str = field(default='/dns', init=False, repr=False)

    # Setters and getters are used to track if attributes have been
    # modified since retiving data from the API
    @property
    def name(self) -> str: # pylint: disable=missing-function-docstring
        return self._name

    @property
    def r_type(self) -> str: # pylint: disable=missing-function-docstring
        return self._r_type

    @property
    def content(self) -> str: # pylint: disable=missing-function-docstring
        return self._content

    @property
    def ttl(self) -> str: # pylint: disable=missing-function-docstring
        return self._ttl

    @property
    def prio(self) -> str: # pylint: disable=missing-function-docstring
        return self._prio

    @property
    def notes(self) -> str: # pylint: disable=missing-function-docstring
        return self._notes

    @name.setter
    def name(self, name: str):
        name = name.removesuffix(f'.{self.domain}')
        self._name = name
        self.state = 'NOT_SYNC'

    @r_type.setter
    def r_type(self, r_type: str):
        assert r_type in SUPPORTED_DNS_RECORD_TYPES

        self._r_type = r_type
        self.state = 'NOT_SYNC'

    @content.setter
    def content(self, content):
        self._content = content
        self.state = 'NOT_SYNC'

    @ttl.setter
    def ttl(self, ttl):
        self._ttl = ttl
        self.state = 'NOT_SYNC'

    @prio.setter
    def prio(self, prio):
        self._prio = prio
        self.state = 'NOT_SYNC'

    @notes.setter
    def notes(self, notes):
        self._notes = notes
        self.state = 'NOT_SYNC'

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
                               record['name'],
                               record['type'],
                               record['content'],
                               record['ttl'],
                               record['prio'],
                               record['notes'],
                               record['id'],
                               'SYNC'))
        return records

    @classmethod
    def get_record(cls,
                   domain: str,
                   r_type: str = None,
                   name: str = None,
                   r_id: str = None) -> 'Dns':
        """Get a specific DNS record

        Usage:
        Either provide the record name and type (r_type),
        or the record ID.

        Example 1, Get by record name and type:
        >>> x = pyrkbun.dns.get_record('example.com', 'A', 'www')

        Example 2, Get by record ID:
        >>> x = pyrkbun.dns.get_record('example.com', r_id ='253440859')
        """
        if r_type:
            assert r_type in SUPPORTED_DNS_RECORD_TYPES

        path = f'{cls.__api_path}/retrieve/{domain}/{r_id}' if r_id \
            else f'{cls.__api_path}/retrieveByNameType/{domain}/{r_type}/{name}'

        response = api_post(path)
        records = cls.__cls_creator_formatter(domain, response)
        return records[0]


    @classmethod
    def get_all_records(cls, domain: str) -> list['Dns']:
        """Get all DNS records

        Example:
        >>> x = pyrkbun.dns.get_all_records('example.com')
        """
        path = f'{cls.__api_path}/retrieve/{domain}'

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
                      r_type: str = None,
                      name: str = None,
                      r_id: str = None) -> dict:
        """Delete a specific DNS record

        Usage:
        Either provide the record name and type (r_type),
        or the record ID.

        Example 1, Get by record name and type:
        >>> x = pyrkbun.dns.delete_record('example.com', 'A', 'www')

        Example 2, Get by record ID:
        >>> x = pyrkbun.dns.delete_record('example.com', r_id ='253440859')
        """
        if r_type:
            assert r_type in SUPPORTED_DNS_RECORD_TYPES

        path = f'{cls.__api_path}/retrieve/{domain}/{r_id}' if r_id \
            else f'{cls.__api_path}/deleteByNameType/{domain}/{r_type}/{name}'
        response = api_post(path)
        return response

    @classmethod
    def edit_record(cls,
                    domain: str,
                    updates: dict,
                    r_type: str = None,
                    name: str = None,
                    r_id: str = None) -> dict:
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
        if r_type:
            assert r_type in SUPPORTED_DNS_RECORD_TYPES

        path = f'{cls.__api_path}/edit/{domain}/{r_id}' if r_id \
            else f'{cls.__api_path}/editByNameType/{domain}/{r_type}/{name}'
        response = api_post(path, updates)
        return response

    def refresh(self) -> dict:
        """Refresh DNS class instance details from API
        """
        path = f'{self.__api_path}/retrieve/{self.domain}/{self.r_id}'
        response = api_post(path)
        if 'notes' not in response['records'][0].keys():
            response['records'][0]['notes'] = ''
        self.name = response['records'][0]['name']
        self.r_type = response['records'][0]['type']
        self.content= response['records'][0]['content']
        self.ttl = response['records'][0]['ttl']
        self.prio = response['records'][0]['prio']
        self.notes = response['records'][0]['notes']
        self.r_id = response['records'][0]['id']
        self.state = 'SYNC'
        return response

    def create(self) -> dict:
        """Create record based on class instance attributes
        """
        path = f'{self.__api_path}/create/{self.domain}'
        payload = {'name': self.name,
                   'type': self.r_type,
                   'content': self.content,
                   'ttl': self.ttl,
                   'prio': self.prio,
                   'notes': self.notes}
        response = api_post(path, payload)
        self.r_id = response['id']
        self.state = 'SYNC'
        return response

    def update(self) -> dict:
        """Update record based on class instance attributes

        Note: Attempting an update without any valid changes to the DNS
        record will result in an API Error.
        """
        path = f'{self.__api_path}/edit/{self.domain}/{self.r_id}'
        payload = {'name': self.name,
                   'type': self.r_type,
                   'content': self.content,
                   'ttl': self.ttl,
                   'prio': self.prio,
                   'notes': self.notes}
        response = api_post(path, payload)
        self.state = 'SYNC'
        return response

    def delete(self) -> dict:
        """Delete DNS record represented by class instance
        """
        path = f'{self.__api_path}/delete/{self.domain}/{self.r_id}'
        response = api_post(path)
        self.state = 'DELETED'
        return response
