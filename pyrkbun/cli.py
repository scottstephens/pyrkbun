"""CLI Interface to pyrkbun
"""
#! /usr/local/bin/python
import json
import argparse
from os import getenv
from colorama import init, Fore, Back, Style

from . import ssl
from . import pricing
from .dns import Dns as dns
from .util import api_ping
from .const import ApiError, ApiFailure

# init colorama
init(autoreset=True)

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

def check_api_creds() -> bool:
    """CHeck API Creds have been set"""
    check_api_key: str = getenv('PYRK_API_KEY')
    check_api_secret: str = getenv('PYRK_API_SECRET_KEY')

    if not check_api_key:
        print(f'{Fore.RED}API Key has not been set. Set enironment varaibale' +
            f'{Fore.RED} "export PYRK_API_KEY=<your_api_key>"')
        return False

    if not check_api_secret:
        print(f'{Fore.RED}API Secret Key has not been set. Set enironment varaibale' +
            f'{Fore.RED} "export PYRK_API_SECRET_KEY=<your_api_secret_key>"')
        return False

    return True

def run_ping(args: argparse.Namespace) -> str:
    """Run Ping"""
    result: dict = api_ping(args.v4)
    return json.dumps(result)

def run_pricing(args: argparse.Namespace) -> str: # pylint: disable = unused-argument
    """Run Picing"""
    result: dict = pricing.get()
    return json.dumps(result)

def run_ssl(args: argparse.Namespace) -> str:
    """Run SSL"""
    result: dict = ssl.get(args.domain)
    return json.dumps(result)

def run_dns(args: argparse.Namespace) -> str: # pylint: disable = too-many-branches
    """Run DNS"""
    try:
        command: str = args.command
    except AttributeError:
        return 'Please choose from get, create, edit, delete, or restore'

    domain: str = args.domain
    record_id: str = args.id
    record_type: str = args.type
    name: str = args.name
    content: str = args.content
    ttl: str = args.ttl
    priority: str = args.priority
    notes: str = args.notes

    if command in ('create', 'edit'):
        record = {'name': name,
                  'type': record_type,
                  'content': content,
                  'ttl': ttl,
                  'prio': priority,
                  'notes': notes}
    try:
        if command == 'get':
            if record_id:
                records = dns.get_records(domain, record_id=record_id)
            elif name and record_type:
                records = dns.get_records(domain, record_type, name)
            else:
                records = dns.get_records(domain)

            result = []
            for record in records:
                modified_record = record.__dict__
                modified_record['type'] = modified_record.pop('record_type')
                modified_record['id'] = modified_record.pop('record_id')
                modified_record.pop('domain', None)
                result.append(modified_record)

        elif command == 'create':
            result = dns.create_record(domain, record)

        elif command == 'edit':
            if record_id:
                result = dns.edit_record(domain, record, record_id=record_id)
            elif name and record_type:
                result = dns.edit_record(domain, record, record_type, name)
            else:
                return f'{Fore.RED}Please set value for either "-id" OR "-name" and "-type"'

        elif command == 'delete':
            if record_id:
                result = dns.delete_record(domain, record_id=record_id)
            elif name and record_type:
                result = dns.delete_record(domain, record_type, name)
            else:
                return f'{Fore.RED}Please set value for either "-id" OR "-name" and "-type"'

    except (ApiError, ApiFailure) as error:
        return f'{Back.RED}{Fore.YELLOW}API Error -> {error.message}'

    return json.dumps(result)

def run_dns_bulk(args: argparse.Namespace) -> None: # pylint: disable = [too-many-locals, too-many-branches, too-many-statements]
    """Run DNS Bulk
    flush: Delete ALL existing records and load records from provided file
    merge: Update existing records and add new records if they do not yet exist.
        Records not specified in the file will remain unchanged. Existing records
        must include the ID
    add: Add all records in the provided file
    """
    domain: str = args.domain
    input_file: str = args.input
    output_file: str = args.output
    mode: str = args.mode
    created: dict = {'SUCCESS': [], 'FAILURE': []}
    edited: dict = {'SUCCESS': [], 'FAILURE': []}
    deleted: dict = {'SUCCESS': [], 'FAILURE': []}
    not_found: list = []

    # Create, edit and delete fuctions to be called once user options are evaluated
    def create_records(records: list):
        for record in records:
            record.pop('domain', None)
            record.pop('id', None)
            try:
                result = dns.create_record(domain, record)
            except (ApiError, ApiFailure) as error:
                created['FAILURE'].append({'error': error.message, 'record': record})
                print(f'{Back.RED}{Fore.YELLOW}FAILED to CREATE record:{record}')
                continue
            record.update({'id': str(result['id'])})
            print(f'{Fore.GREEN}CREATED record:{record}')
            created['SUCCESS'].append({'result': result, 'record': record})

    def delete_records(records: list):
        for record in records:
            try:
                result = dns.delete_record(domain, record_id=record['id'])
            except (ApiError, ApiFailure) as error:
                deleted['FAILURE'].append({'result': error.message, 'record': record})
                print(f'{Back.RED}{Fore.YELLOW}FAILED to DELETE record:{record}')
                continue
            print(f'{Fore.GREEN}DELETED record:{record}')
            deleted['SUCCESS'].append({'result': result, 'record': record})

    def edit_records(records: list):
        for record in records:
            try:
                record.pop('domain', None)
                record_id = record.pop('id', None)
                result = dns.edit_record(domain, record, record_id=record_id)
                record.update({'id': record_id})
            except (ApiError, ApiFailure) as error:
                edited['FAILURE'].append({'result': error.message, 'record': record})
                print(f'{Back.RED}{Fore.YELLOW}FAILED to EDIT record:{record}')
                continue
            print(f'{Fore.GREEN}EDITED record:{record}{Style.RESET_ALL}')
            edited['SUCCESS'].append({'result': result, 'record': record})

    print(f'{Fore.BLUE}{Style.DIM}Loading updated records from file')
    with open(input_file, 'r', encoding='utf8') as file:
        user_provided_records = json.load(file)

    run_dns_args = argparse.Namespace(domain=domain,
                                      command='get',
                                      id='', name='',
                                      type='',
                                      content='',
                                      ttl='',
                                      priority='',
                                      notes='')

    print(f'{Fore.BLUE}{Style.DIM}Collecting existing records')
    existing_records: dict = json.loads(run_dns(run_dns_args))

    if mode == 'flush':
        delete_records(existing_records)
        create_records(user_provided_records)

    if mode == 'add':
        create_records(user_provided_records)

    if mode == 'merge': # pylint: disable = too-many-nested-blocks
        # This is a somewhat complex collection of loop and if's
        # The goal is to make the cli tolerant to variations in user input
        # that could be expected due to outputs from other commands
        to_edit = []
        to_create = []
        for user_record in user_provided_records:
            # If the id key is present then it should be cheked for editing
            # if not, it should be created (fall through to first else)
            if user_record.get('id') is not None:
                # If the id key is present, but has no value, then assume
                # it should be created as well (fall through to nested else)
                if len(user_record['id']) != 0:
                    for exist_record in existing_records:
                        # If the Id values match between an existing and
                        # and user provided record then we need to edit it
                        if exist_record['id'] == user_record['id']:
                            # Make sure the records are different or else
                            # the API will return an error that it could
                            # not edit the record
                            if exist_record != user_record:
                                print(Fore.BLUE + Style.DIM
                                      + f'Adding record to EDIT list:{user_record}')
                                to_edit.append(user_record)

                else:
                    print(Fore.BLUE + Style.DIM
                          + f'Adding record with EMPTY "id" field to CREATE list:{user_record}')
                    to_create.append(user_record)
            else:
                print(Fore.BLUE + Style.DIM
                      + f'Adding record with NO "id" field to CREATE list:{user_record}')
                to_create.append(user_record)
        # If after the above comparison if the record does not appear in
        # to_create or to_edit, then the ID must have been provided and
        # it must be incorrect
        for user_record in user_provided_records:
            if user_record not in to_create and user_record not in to_edit:
                print(f'{Fore.BLUE}{Style.DIM}Adding record to IGNORE list:{user_record}')
                not_found.append(user_record)
        # create and edit records as required
        create_records(to_create)
        edit_records(to_edit)

    # Format results to be written to file
    result = {'CREATED': created, 'EDITED': edited, 'DELETED': deleted, 'IGNORED': not_found}

    with open(output_file, 'w', encoding='utf8') as file:
        json.dump(result, file)
    print(f'{Fore.GREEN}{Style.BRIGHT}Detailed results written to {output_file}')

def main() -> str: # pylint: disable = too-many-statements
    """"Operate pyrkbun from the command line"""

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='''CLI interface to the pyrkbun python library.
        
Set environment variables for API Key and API Secret Key to authenticate commands.

For API Key set:
'export PYRK_API_KEY=<your_api_key>'

For API Secret Key set:
'export PYRK_API_SECRET_KEY=<your_api_secret_key>'
''')

    pyrkbun_subparser = parser.add_subparsers(help='Pyrkbun Functions')

    ping_parser = pyrkbun_subparser.add_parser('ping', help='Poll API and return IP address')
    ping_parser.set_defaults(func=run_ping)
    ping_parser.add_argument('-v4', action='store_true', help='Force IPv4 Only')

    pricing_parser = pyrkbun_subparser.add_parser('pricing', help='Retrieve pricing information')
    pricing_parser.set_defaults(func=run_pricing)

    ssl_parser = pyrkbun_subparser.add_parser('ssl', help='Retrieve SSL bundle if available')
    ssl_parser.set_defaults(func=run_ssl)
    ssl_parser.add_argument('domain', help='Target domain name')

    dns_parser = pyrkbun_subparser.add_parser('dns', help='Operate DNS records')
    dns_parser.set_defaults(func=run_dns)
    dns_parser.add_argument('domain', help='Target domain')

    dns_subparser = dns_parser.add_subparsers()

    get = dns_subparser.add_parser('get', help='Get a DNS record')
    get.set_defaults(command='get',
                     id='',
                     name='',
                     type='',
                     content='',
                     ttl='',
                     priority='',
                     notes='')
    get.add_argument('-id', help='Porkbun unique record ID')
    get.add_argument('-name', help='DNS record name', type=str)
    get.add_argument('-type', help='DNS record type',
                     type=str, choices=SUPPORTED_DNS_RECORD_TYPES)

    create = dns_subparser.add_parser('create', help='Create a DNS record')
    create.set_defaults(command='create',
                        id='',
                        name='',
                        type='',
                        content='',
                        ttl='',
                        priority='',
                        notes='')
    create.add_argument('-name', help='DNS record name', type=str)
    create.add_argument('-type', help='DNS record type',
                        type=str, choices=SUPPORTED_DNS_RECORD_TYPES)
    create.add_argument('-content', help='DNS record content', type=str)
    create.add_argument('-ttl', help='DNS record ttl', type=str)
    create.add_argument('-priority', help='DNS record priority', type=str)
    create.add_argument('-notes', help='DNS record notes', type=str)

    edit = dns_subparser.add_parser('edit', help='Edit a DNS record: '
                                    + 'You must provide either -id OR -name and -type to identify '
                                    + 'the target record. -id is less ambiguous and is prefered '
                                    + 'as multiple records with the same name and type may exist')
    edit.set_defaults(command='edit',
                      id='',
                      name='',
                      type='',
                      content='',
                      ttl='',
                      priority='',
                      notes='')
    edit.add_argument('-id', help='Porkbun unique record ID')
    edit.add_argument('-name', help='DNS record name', type=str)
    edit.add_argument('-type', help='DNS record type',
                      type=str, choices=SUPPORTED_DNS_RECORD_TYPES)
    edit.add_argument('-content', help='DNS record content', type=str)
    edit.add_argument('-ttl', help='DNS record ttl', type=str)
    edit.add_argument('-priority', help='DNS record priority', type=str)
    edit.add_argument('-notes', help='DNS record notes', type=str)

    delete = dns_subparser.add_parser('delete', help='Delete a DNS record '
                                    + 'You must provide either -id OR -name and -type to identify '
                                    + 'the target record. -id is less ambiguous and is prefered '
                                    + 'as multiple records with the same name and type may exist')
    delete.set_defaults(command='delete',
                        id='',
                        name='',
                        type='',
                        content='',
                        ttl='',
                        priority='',
                        notes='')
    delete.add_argument('-id', help='Delete Record by record ID')
    delete.add_argument('-name', help='DNS record name', type=str)
    delete.add_argument('-type', help='DNS record type',
                        type=str, choices=SUPPORTED_DNS_RECORD_TYPES)

    bulk = dns_subparser.add_parser('bulk', help='Run bulk operations on DNS Service')
    bulk.set_defaults(func=run_dns_bulk, mode='merge')
    bulk.add_argument('input', help='File containing JSON formatted DNS records')
    bulk.add_argument('output', help='File to write results of bulk operation')
    bulk.add_argument('-mode', choices={'flush', 'merge', 'add'},
                      help='Defaults to merge. '
                    + '"add": Add all records in the provided file. '
                    + '"flush": Delete ALL existing records and load records from provided file. '
                    + '"merge": Update existing records and add new records if they do not yet '
                    + 'exist. Records not specified in the file will remain unchanged.  '
                    + 'Existing records must include the record ID.')

    args = parser.parse_args()

    if not check_api_creds():
        return

    result = args.func(args)
    if result:
        print(result)

if __name__ == "__main__":
    main()
