# pyrkbun - Python library and CLI for the porkbun.com API

[![pypi](https://img.shields.io/pypi/v/pyrkbun)](https://pypi.org/project/pyrkbun/)
[![GitHub release](https://img.shields.io/github/release/jxg81/pyrkbun.svg)](https://github.com/jxg81/pyrkbun/releases)
[![Hex.pm](https://img.shields.io/hexpm/l/plug)](https://www.apache.org/licenses/LICENSE-2.0)

[![Github CI](https://github.com/jxg81/pyrkbun/actions/workflows/python-test.yml/badge.svg)](https://github.com/jxg81/pyrkbun/actions)
[![Github CD](https://github.com/jxg81/pyrkbun/actions/workflows/python-publish.yml/badge.svg)](https://github.com/jxg81/pyrkbun/actions)


[![paypal](https://img.shields.io/badge/donate-paypal-blue)](https://www.paypal.com/donate/?business=MP4ZR6WS8UPX8&no_recurring=0&item_name=%28jxg81%29+-+Thanks+for+your+support.&currency_code=AUD)

pyrkbun is an unoffical python library for interfacing with the porkbun.com API
# Contents
- [Getting Started](#getting-started)
  - [Installation](#installation)
  - [Enable porkbun.com API access](#enable-porkbuncom-api-access)
  - [Configure Environment](#configure-environment)
- [Using pyrkbun in your python project](#using-pyrkbun-in-your-python-project)
  - [pyrkbun ssl](#pyrkbun-ssl)
  - [pyrkbun pricing](#pyrkbun-pricing)
  - [pyrkbun dns](#pyrkbun-dns)
    - [dns class instantiation](#dns-class-instantiation)
    - [dns class methods](#dns-class-methods)
    - [Getting help on working with dns](#getting-help-on-working-with-dns)
  - [pyrkbun ping](#pyrkbun-ping)
- [Using pyrkbun CLI from the terminal (Beta)](#using-pyrkbun-cli-from-the-terminal-beta)
  - [pyrkbun cli ssl](#pyrkbun-cli-ssl)
  - [pyrkbun cli pricing](#pyrkbun-cli-pricing)
  - [pyrkbun cli dns](#pyrkbun-cli-dns)
    - [get record(s)](#get-records)
    - [create record](#create-record)
    - [edit record](#edit-record)
    - [delete record](#delete-record)
    - [bulk operations](#bulk-operations)
  - [pyrkbun cli ping](#pyrkbun-cli-ping)
# Getting Started
## Installation
Install pyrkbun using pip.

```
pip install pyrkbun
```
## Enable porkbun.com API access
You will need to ensure that you have API access enabled for your domain and an API Access Key / Secret Key. Details on how to configure your domain for API access can be found on the [porkbun website](https://kb.porkbun.com/article/190-getting-started-with-the-porkbun-api)

## Configure Environment
Before using pyrkbun you will need to set a couple of envorinment variables to hold your API credentails.
```
export PYRK_API_SECRET_KEY='sk_abcdef123456789abcdef123456789abcdef'
export PYRK_API_KEY = 'sk_abcdef123456789abcdef123456789abcdef'
```
By default pyrkbun will utilise the default porkbun.com API endpoint which supports both IPv4 and IPv6. To force IPv4 only you can set an additional environement variable as follows.
```
export PYRK_FORCE_V4=True
```
If you are on a low latency path to the Porkbun service you may hit API rate limits and get 503 returned from the API resulting in ApiFailure exception being raised. You can set a rate limit environment variable to automatically add a delay in seconds before each API call. If this variable is not set no dealy will be addded.
```
export PYRK_RATE=1.5
```
# Using pyrkbun in your python project
pyrkbun exposes all of the porkbun.com api functionality through a set of functions and classes. Functionality is grouped into sub-modules as follows:
 - **pyrkbun.ssl:** Operations related to certificate management.  Exposes a single function to reirieve certifcate bundle.
 - **pyrkbun.pricing:** Operations relating to retrival of domain pricing information. Exposes a single function to retrieve pricing information.
 - **pyrkbun.dns:** Operations relating to DNS management. This is the bulk of the functionality.

## pyrkbun ssl
Retrieve porkbun.com provided wildcard cert bundle for your domain.
 ```python
>>> import pyrkbun
>>> x = pyrkbun.ssl.get()
>>> print(x)
{'status': 'SUCCESS',
'intermediatecertificate': '<cert-data>',
'certificatechain': '<cert-data>',
'privatekey': "<cert-data>",
'publickey': '<cert-data>'}

 ```
## pyrkbun pricing
Retrieve porkbun.com default domain pricing data.
 ```python
>>> import pyrkbun
>>> x = pyrkbun.pricing.get()
>>> print(x)
{'status': 'SUCCESS',
'pricing': {'de': {'registration': '5.55', 'renewal': '4.11',
'transfer': '4.11', 'coupons': {'registration':
{'code': 'AWESOMENESS', 'max_per_user': 1, 'first_year_only': 'yes',
'type': 'amount', 'amount': 1}}},
'xof': {'registration': '6.49', 'renewal': '21.94', ... }
```
## pyrkbun dns
DNS comprises the bulk of the functionality of pyrkbun. The dns submodule defines a class for interacting with the DNS api. You can either instantiate class instances and use the exposed instance methods, or execute class methods to interact with the API without the need to instantiate a class instance.

NOTE: When defining hostnames for A, AAAA, CNAME and ALIAS records, you should always provide the unqualified name. (e.g. if your domain is example.com, provide hostnames as 'www' not 'www.example.com').

### dns class instantiation
The following example shows how to instantiate a class instance and create, update and delete a DNS record.
 ```python
>>> import pyrkbun

# Instantiate class instance representing 'www' A record with IP of '198.51.100.45' and ttl of 620 in domain example.com
>>> x = pyrkbun.dns('example.com',
                    'A',
                    '198.51.100.45',
                    'www',
                    '620',
                    '0') 

# Call porkbun API to create DNS record from class data
>>> x.create() 
{'status': 'SUCCESS', 'id': 253916852}

# Update hostname
>>> x.name = 'website' 

# Call porkbun API to update DNS record with new hostname
>>> x.update()
{'status': 'SUCCESS'}

# Refresh record data held in class instance (in case updates were made out of band)
>>> x.refresh()
{'status': 'SUCCESS'}

# Delete the record
>>> x.delete()
{'status': 'SUCCESS'}
```

### dns class methods
The following example shows how to create, update and delete a DNS record using the provided class methods.
 ```python
>>> import pyrkbun

# Create dict containd data for a 'www' A record with IP of '198.51.100.45' and ttl of 620 in domain example.com
>>> record = {'name': 'www',
            'type': 'A',
            'content': '198.51.100.45',
            'ttl': '620',
            'prio': '0'}

# Call porkbun API to create record
>>> x = pyrkbun.dns.create_record('example.com', record)
>>> print(x)
{'status': 'SUCCESS', 'id': 253475380}

# Create record containing updates
>>> update = {'name': 'website',
            'type': 'A',
            'content': '198.51.100.45',
            'ttl': '620',
            'prio': '0'}

# Call porkbun API to update DNS record
>>> x = pyrkbun.dns.update_record('example.com', update)
>>> print(x)
{'status': 'SUCCESS'}

# Delete the record by name and type
>>> x = pyrkbun.dns.delete_record('example.com', 'A', 'www')
>>> print(x)
{'status': 'SUCCESS'}
```

A class method is exposed to collect existing domain records. The method will return a list of class instances for each record returned. Arguments can be provided to the method to select specific records or set of records to be returned. To collect all records for a domain simply provide the domain name as the only argument.
```python
>>> import pyrkbun

>>> x = pyrkbun.dns.get_records('example.com')
>>> print(x)
[Dns(domain='example.com', name='www', record_type='A',
content='198.51.100.45', ttl='650', prio='0', notes='',
record_id='253440859'), Dns(domain='example.com', .... ]
```

### Getting help on working with dns
All methods and functions are fully documented, additional detail on working with pyrkbun is available via the python help function.
```python
>>> import pyrkbun

>>> help(pyrkbun.dns)
...
```

## pyrkbun ping
Porkbun provides a simple API endpoint for polling the API and returning your current IP address. This can be useful for usecases such as dynamic dns record creation. This is exposed in pyrkbun as ***pyrkbun.ping***
```python
>>> import pyrkbun

# Ping porkbun API and return IP
>>> x = pyrkbun.ping()
>>> print(x)
{'status': 'SUCCESS', 'yourIp': '2001:0db8:85a3:0000:0000:8a2e:0370:7334'}

# Ping porkbun API and force the use of IPv4
>>> x = pyrkbun.ping(ipv4=True)
>>> print(x)
{'status': 'SUCCESS', 'yourIp': '198.51.100.45'}
```

# Using pyrkbun CLI from the terminal (BETA)
You can utilise the functionality of pyrkbun directly from the terminal without the need to write your own python code.

The cli interface is availble uusing the command `pyrkbun`

Help is available from the command line
```
% pyrkbun -h
usage: cli.py [-h] {ping,pricing,ssl,dns} ...

CLI interface to the pyrkbun python library.
        
Set environment variables for API Key and API Secret Key to authenticate commands.

For API Key set:
'export PYRK_API_KEY=<your_api_key>'

For API Secret Key set:
'export PYRK_API_SECRET_KEY=<your_api_secret_key>'

positional arguments:
  {ping,pricing,ssl,dns}
                        Pyrkbun Functions
    ping                Poll API and return IP address
    pricing             Retrieve pricing information
    ssl                 Retrieve SSL bundle if available
    dns                 Operate DNS records

options:
  -h, --help            show this help message and exit
```

## pyrkbun cli ssl
Retrieve porkbun.com provided wildcard cert bundle for your domain.
```
% pyrkbun ssl example.com
{"status": "SUCCESS",
"intermediatecertificate": "<cert-data>",
"certificatechain": "<cert-data>",
"privatekey": "<cert-data>",
"publickey": "<cert-data>"}
```
## pyrkbun cli pricing
Retrieve porkbun.com default domain pricing data.
```
% pyrkbun pricing
{"status": "SUCCESS",
"pricing": {"de": {"registration": "5.55", "renewal": "4.11",
"transfer": "4.11", "coupons": {"registration":
{"code": "AWESOMENESS", "max_per_user": 1, "first_year_only": "yes",
"type": "amount", "amount": 1}}},
"xof": {"registration": "6.49", "renewal": "21.94", ... }
```
## pyrkbun cli dns

### get record(s)
Get all records for a domain
```
% pyrkbun dns example.com get
[{"name": "www", "type": "A", "content": "198.51.100.45", "ttl": "650", "prio": "0", "notes": "", "id": "253440859"}, {"name": "mail", .... ]
```
Get a single record by ID
```
% pyrkbun dns example.com get -id 253440859
[{"name": "www", "type": "A", "content": "198.51.100.45", "ttl": "650", "prio": "0", "notes": "", "id": "253440859"}]
```
Get a single record by name and type
```
% pyrkbun dns example.com get -name www -type A
[{"name": "www", "type": "A", "content": "198.51.100.45", "ttl": "650", "prio": "0", "notes": "", "id": "253440859"}]
```
### create record
Create a new record - Operation status and new record ID will be returned 
```
% pyrkbun dns example.com create -name www -type A -content "198.51.100.45" -ttl 650
{"status": "SUCCESS", "id": 256365177}
```
Utilise help for details on all available options `pyrkbun dns example.com create -h`
### edit record
Edit a record - Operation status will be returned

Records can be selected by either unique ID or by name and type. ID is less ambiguous and is prefered as multiple records with the same name and type may exist.

Edit by ID
```
% pyrkbun dns example.com edit -id 256365177 -content "198.51.100.46"
{"status": "SUCCESS"}
```

Edit by name and type
```
% pyrkbun dns example.com edit -name www -type A -content "198.51.100.46"
{"status": "SUCCESS"}
```
Utilise help for details on all available options `pyrkbun dns example.com create -h`

NOTE: If you attempt to update a record with no changes the API will return an error
### delete record
Delete a record - Operation status will be returned

Records can be selected by either unique ID or by name and type. ID is less ambiguous and is prefered as multiple records with the same name and type may exist.

Edit by ID
```
% pyrkbun dns example.com delete -id 256365177
{"status": "SUCCESS"}
```

Edit by name and type
```
% pyrkbun dns example.com edit -name www -type A
{"status": "SUCCESS"}
```
### bulk operations
Perfrom bulk operations on domain records by provding a json file containg record data. The command requires an input json file, output file (to write operation results) and mode.

The following modes are supported:

**add**: Add all records in the provided file.  
**flush**: Delete ALL existing records and load records from provided file.  
**merge (default)**: Update existing records and add new records if they do not yet exist. Records not specified in the file will remain unchanged and no records will be deleted. Existing records to be updated MUST include the record ID.

Example usage:
```
% pyrkbun dns example.com bulk ./records.json ./result.json -mode merge
```

Example input file:
```json
[
// Existing record to be updated - note inclusion of ID
// Record id's are only required when using the 'merge' mode and only for existing records to be updated with new data
    {
        "content": "198.51.100.46",
        "name": "www",
        "ttl": "600",
        "prio": "0",
        "notes": "Company Website",
        "type": "A",
        "id": "256365177"
    },
// New record to be created - id field is not required
// When using the 'flush' or 'add' modes record id's are never required
    {
        "content": "mail.example.com",
        "name": "",
        "ttl": "600",
        "prio": "10",
        "notes": "Primary MX Record",
        "type": "MX",
    }
]
```
NOTE: If you attempt to update a record with no changes the API will return an error
## pyrkbun cli ping
Porkbun provides a simple API endpoint for polling the API and returning your current IP address.

Ping utilising the default v4/v6 endpoint

```
% pyrkbun ping
{"status": "SUCCESS", "yourIp": "2001:0db8:85a3:0000:0000:8a2e:0370:7334"}
```
Ping utilising the v4 only endpoint
```
% pyrkbun ping -v4
{"status": "SUCCESS", "yourIp": "198.51.100.45"}
```