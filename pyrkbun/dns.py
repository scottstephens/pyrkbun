"""Porkbun DNS API
"""
from dataclasses import dataclass, field
from .const import DnsRecordType
from .util import api_post

@dataclass
class Dns():
    '''Class representing a DNS record
    '''

    # Just the right number of instance attributes
    # pylint: disable=too-many-instance-attributes
    domain: str
    name: str
    r_type: DnsRecordType
    content: str
    ttl: str
    prio: str
    notes: str = ''
    r_id: str = ''
    state: str = 'NOT-SYNC'

    _name: str = field(init=False, repr=False)
    _r_type: DnsRecordType = field(init=False, repr=False)
    _content: str = field(init=False, repr=False)
    _ttl: str = field(init=False, repr=False)
    _prio: str = field(init=False, repr=False)
    _notes: str = field(init=False, repr=False)

    __api_path: str = field(default='/dns', init=False, repr=False)

    # Setters and getters are used to track if attributes have been
    # modified since retiving data from the API
    @property
    def name(self) -> str:
        return self._name

    @property
    def r_type(self) -> DnsRecordType:
        return self._r_type

    @property
    def content(self) -> str:
        return self._content

    @property
    def ttl(self) -> str:
        return self._ttl

    @property
    def prio(self) -> str:
        return self._prio

    @property
    def notes(self) -> str:
        return self._notes

    @name.setter
    def name(self, name: str):
        name = name.removesuffix(f'.{self.domain}')
        self.state = 'NOT-SYNC' if name != self.name else 'SYNC'
        self._name = name

    @r_type.setter
    def r_type(self, r_type: DnsRecordType):
        self.state = 'NOT-SYNC' if r_type != self.r_type else 'SYNC'
        self._r_type = r_type

    @content.setter
    def content(self, content):
        self.state = 'NOT-SYNC' if content != self.content else 'SYNC'
        self._content = content

    @ttl.setter
    def ttl(self, ttl):
        self.state = 'NOT-SYNC' if ttl != self.ttl else 'SYNC'
        self._ttl = ttl

    @prio.setter
    def prio(self, prio):
        self.state = 'NOT-SYNC' if prio != self.prio else 'SYNC'
        self._prio = prio

    @notes.setter
    def notes(self, notes):
        self.state = 'NOT-SYNC' if notes != self.notes else 'SYNC'
        self._notes = notes

    @classmethod
    def get_record(cls,
                   domain: str,
                   r_type: DnsRecordType = '',
                   name: str = '',
                   r_id: str = ''):
        path = f'{cls.__api_path}/retrieve/{domain}/{r_id}' if r_id \
            else f'{cls.__api_path}/retrieveByNameType/{domain}/{r_type}/{name}'
        records = []

        response = api_post(path)
        for record in response['records']:
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
        return records[0]


    @classmethod
    def get_records(cls,
                    domain: str,
                    r_type: DnsRecordType = ''):
        path = f'{cls.__api_path}/retrieveByNameType/{domain}/{r_type}' if r_type \
            else f'{cls.__api_path}/retrieve/{domain}'
        records = []

        response = api_post(path)
        for record in response['records']:
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
    def create_record(cls,
                      domain: str,
                      name: str,
                      r_type: DnsRecordType,
                      content: str,
                      notes: str = '',
                      ttl: str= '600',
                      prio: str = '0'):
        path = f'{cls.__api_path}/create/{domain}/'
        payload = {'name': name,
                   'type': r_type,
                   'content': content,
                   'ttl': ttl,
                   'notes': notes}
        
        response = api_post(path, payload)
        if response['status'] == 'SUCCESS':
            return cls(domain,
                       name,
                       r_type,
                       content,
                       ttl,
                       prio,
                       notes,
                       response['id'],
                       'SYNC')

    @classmethod
    def delete_record(cls,
                      domain: str,
                      r_type: DnsRecordType = '',
                      name: str = '',
                      r_id: str = ''):
        path = f'{cls.__api_path}/retrieve/{domain}/{r_id}' if r_id \
            else f'{cls.__api_path}/deleteByNameType/{domain}/{r_type}/{name}'
        response = api_post(path)
        return response

    @classmethod
    def delete_records(cls,
                       domain: str,
                       r_type: DnsRecordType = ''):
        path = f'{cls.__api_path}/deleteByNameType/{domain}/{r_type}'
        response = api_post(path)
        return response

    @classmethod
    def edit_record(cls,
                    domain: str,
                    r_type: DnsRecordType = '',
                    name: str = '',
                    r_id: str = '',
                    new_name: str = '',
                    new_type: DnsRecordType = '',
                    content: str = '',
                    ttl: str = '',
                    prio: str = '',
                    notes: str = ''):
        path = f'{cls.__api_path}/edit/{domain}/{r_id}' if r_id \
            else f'{cls.__api_path}/editByNameType/{domain}/{r_type}/{name}'
        payload = {}
        # Disable expression-not-assigned for this method
        # pylint: disable=expression-not-assigned
        payload.update({'name': new_name}) if new_name else None
        payload.update({'type': new_type}) if new_type else None
        payload.update({'content': content}) if content else None
        payload.update({'ttl': ttl}) if ttl else None
        payload.update({'ttl': prio}) if prio else None
        payload.update({'notes': notes}) if notes else None
        response = api_post(path, payload)
        return response

    def refresh(self):
        """Refresh local state from API
        """
        path = f'{self.__api_path}/retrieve/{self.domain}/{self.r_id}'
        response = api_post(path)
        if response['status'] == 'SUCCESS':
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

    def create(self):
        """Create record
        """
        path = f'{self.__api_path}/create/{self.domain}'
        payload = {'name': self.name,
                   'type': self.r_type,
                   'content': self.content,
                   'ttl': self.ttl,
                   'notes': self.notes}
        response = api_post(path, payload)
        if response['status'] == 'SUCCESS':
            self.r_id = response['id']
            self.state = 'SYNC'
        return response

    def update(self):
        """Push record updates
        
        Note: Attempting an update without any valid changes to the DNS
        record will result in an API Error.
        """
        path = f'{self.__api_path}/edit/{self.domain}/{self.r_id}'
        payload = {'name': self.name,
                   'type': self.r_type,
                   'content': self.content,
                   'ttl': self.ttl,
                   'notes': self.notes}
        response = api_post(path, payload)
        self.state = 'SYNC' if response['status'] == 'SUCCESS' else self.state
        return response

    def delete(self):
        """Delete record
        """
        path = f'{self.__api_path}/delete/{self.domain}/{self.r_id}'
        response = api_post(path)
        self.state = 'DELETED' if response['status'] == 'SUCCESS' else self.state
        return response
