"""CLI Interface to pyrkbun
"""
#! /usr/local/bin/python
import json
import argparse
from dataclasses import asdict
from os import getenv
from colorama import init, Fore, Back, Style

from .client import PyrkbunClient, ApiError, ApiFailure
from .dns import Dns
from .ssl import Ssl
from .pricing import Pricing

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

def get_client() -> PyrkbunClient:
    """Get a configured PyrkbunClient"""
    try:
        return PyrkbunClient.build()
    except ValueError as e:
        if "api_key and api_secret_key are required" in str(e):
            print(f'{Fore.RED}API credentials not configured.')
            print(f'{Fore.RED}Set environment variables:')
            print(f'{Fore.RED}  export PYRK_API_KEY=<your_api_key>')
            print(f'{Fore.RED}  export PYRK_API_SECRET_KEY=<your_api_secret_key>')
        raise SystemExit(1) from e

# Create, edit and delete fuctions to be called once user options are evaluated
def create_records(domain, records: list, client: PyrkbunClient):
    """Create records in target domain based on supplied records
    """
    dns = Dns(client)
    created: dict = {'SUCCESS': [], 'FAILURE': []}
    for record in records:
        record.pop('domain', None)
        record.pop('id', None)
        try:
            result = dns.create_record(
                domain, 
                record['type'], 
                record['content'],
                name=record.get('name'),
                ttl=record.get('ttl'),
                prio=record.get('priority'),
                notes=record.get('notes')
            )
        except (ApiError, ApiFailure, RuntimeError) as error:
            created['FAILURE'].append({'result': str(error), 'record': record})
            print(f'{Back.RED}{Fore.YELLOW}FAILED to CREATE record:{record}')
            continue
        record.update({'id': result.id})
        print(f'{Fore.GREEN}CREATED record:{record}')
        created['SUCCESS'].append({'result': asdict(result), 'record': record})
    return created

def delete_records(domain, records: list, client: PyrkbunClient):
    """Delete records in target domain based on supplied records
    """
    dns = Dns(client)
    deleted: dict = {'SUCCESS': [], 'FAILURE': []}
    for record in records:
        try:
            dns.delete_record(domain, record_id=record['id'])
        except (ApiError, ApiFailure, RuntimeError) as error:
            deleted['FAILURE'].append({'result': str(error), 'record': record})
            print(f'{Back.RED}{Fore.YELLOW}FAILED to DELETE record:{record}')
            continue
        print(f'{Fore.GREEN}DELETED record:{record}')
        deleted['SUCCESS'].append({'result': 'SUCCESS', 'record': record})
    return deleted

def edit_records(domain, records: list, client: PyrkbunClient):
    """Edit records in target domain based on supplied records
    """
    dns = Dns(client)
    edited: dict = {'SUCCESS': [], 'FAILURE': []}
    for record in records:
        try:
            record.pop('domain', None)
            record_id = record.pop('id', None)
            result = dns.edit_record(
                domain,
                record_id=record_id,
                record_type=record.get('type'),
                name=record.get('name'),
                content=record.get('content'),
                ttl=record.get('ttl'),
                prio=record.get('priority'),
                notes=record.get('notes')
            )
            record.update({'id': record_id})
        except (ApiError, ApiFailure, RuntimeError) as error:
            edited['FAILURE'].append({'result': str(error), 'record': record})
            print(f'{Back.RED}{Fore.YELLOW}FAILED to EDIT record:{record}')
            continue
        print(f'{Fore.GREEN}EDITED record:{record}{Style.RESET_ALL}')
        edited['SUCCESS'].append({'result': asdict(result), 'record': record})
    return edited

def run_ping(args: argparse.Namespace) -> str:
    """Run Ping"""
    try:
        client = get_client()
        result = client.ping(args.v4)
    except (ApiError, ApiFailure, RuntimeError) as error:
        return f'{Back.RED}{Fore.YELLOW}Error -> {error}'
    return json.dumps(result)

def run_pricing(args: argparse.Namespace) -> str: # pylint: disable = unused-argument
    """Run Pricing"""
    try:
        client = get_client()
        pricing = Pricing(client)
        result = pricing.get()
        return json.dumps(asdict(result))
    except (ApiError, ApiFailure, RuntimeError) as error:
        return f'{Back.RED}{Fore.YELLOW}Error -> {error}'

def run_ssl(args: argparse.Namespace) -> str:
    """Run SSL"""
    try:
        client = get_client()
        ssl = Ssl(client)
        result = ssl.get(args.domain)
        return json.dumps(asdict(result))
    except (ApiError, ApiFailure, RuntimeError) as error:
        return f'{Back.RED}{Fore.YELLOW}Error -> {error}'

def run_dns(args: argparse.Namespace) -> str: # pylint: disable = too-many-branches
    """Run DNS"""
    try:
        command: str = args.command
    except AttributeError:
        return 'Please choose from get, create, edit, delete, or restore'

    try:
        client = get_client()
        dns = Dns(client)
        
        domain: str = args.domain
        record_id: str = args.id
        record_type: str = args.type
        name: str = args.name
        content: str = args.content
        ttl: str = args.ttl
        priority: str = args.priority
        notes: str = args.notes

        if command == 'get':
            if record_id:
                response = dns.get_records(domain, record_id=record_id)
            elif name and record_type:
                response = dns.get_records(domain, record_type=record_type, name=name)
            elif record_type:
                response = dns.get_records(domain, record_type=record_type)
            else:
                response = dns.get_records(domain)

            # Convert DnsRecord objects to dict format for CLI output
            result = []
            for record in response.records:
                record_dict = asdict(record)
                # Rename fields to match CLI expectations
                record_dict['type'] = record_dict.pop('type')
                record_dict['id'] = record_dict.pop('id')
                result.append(record_dict)
            
            return json.dumps(result)

        elif command == 'create':
            result = dns.create_record(
                domain, 
                record_type, 
                content,
                name=name if name else None,
                ttl=ttl if ttl else None,
                prio=priority if priority else None,
                notes=notes if notes else None
            )
            return json.dumps(asdict(result))

        elif command == 'edit':
            if record_id:
                result = dns.edit_record(
                    domain, 
                    record_id=record_id,
                    record_type=record_type if record_type else None,
                    name=name if name else None,
                    content=content if content else None,
                    ttl=ttl if ttl else None,
                    prio=priority if priority else None,
                    notes=notes if notes else None
                )
            elif name and record_type:
                result = dns.edit_record(
                    domain,
                    record_type=record_type,
                    name=name,
                    content=content if content else None,
                    ttl=ttl if ttl else None,
                    prio=priority if priority else None,
                    notes=notes if notes else None
                )
            else:
                return f'{Fore.RED}Please set value for either "-id" OR "-name" and "-type"'
            
            return json.dumps(asdict(result))

        elif command == 'delete':
            if record_id:
                dns.delete_record(domain, record_id=record_id)
            elif name and record_type:
                dns.delete_record(domain, record_type=record_type, name=name)
            else:
                return f'{Fore.RED}Please set value for either "-id" OR "-name" and "-type"'
            
            return json.dumps({'status': 'SUCCESS'})

    except (ApiError, ApiFailure, RuntimeError) as error:
        return f'{Back.RED}{Fore.YELLOW}Error -> {error}'

    return json.dumps({'status': 'ERROR', 'message': 'Unknown command'})

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
    ignored: list = []
    include_ns: bool = args.incns

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
    existing_records = json.loads(run_dns(run_dns_args))
    client = get_client()

    # Remove NS records from all operations unless explicitly included
    if not include_ns:
        existing_records = [record for record in existing_records if record['type'] != 'NS']
        user_provided_records = [record for record in user_provided_records if record['type'] != 'NS'] #pylint: disable=line-too-long

    if mode == 'flush':
        deleted = delete_records(domain, existing_records, client)
        created = create_records(domain, user_provided_records, client)

    if mode == 'add':
        created = create_records(domain, user_provided_records, client)

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
                ignored.append(user_record)
        # create and edit records as required
        created = create_records(domain, to_create, client)
        edited = edit_records(domain, to_edit, client)

    # Format results to be written to file
    result = {'CREATED': created, 'EDITED': edited, 'DELETED': deleted, 'IGNORED': ignored}

    with open(output_file, 'w', encoding='utf8') as file:
        json.dump(result, file)
    print(f'{Fore.GREEN}{Style.BRIGHT}Detailed results written to {output_file}')

def main() -> None: # pylint: disable = too-many-statements
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
    bulk.add_argument('-incns', action='store_true', help='Include Name Server Records')
    bulk.add_argument('-mode', choices={'flush', 'merge', 'add'},
                      help='Defaults to merge. '
                    + '"add": Add all records in the provided file. '
                    + '"flush": Delete ALL existing records and load records from provided file. '
                    + '"merge": Update existing records and add new records if they do not yet '
                    + 'exist. Records not specified in the file will remain unchanged.  '
                    + 'Existing records must include the record ID.')

    args = parser.parse_args()

    result = args.func(args)
    if result:
        print(result)

if __name__ == "__main__":
    main()
