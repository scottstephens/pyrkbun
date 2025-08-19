"""Constants for Porkbun API
"""

VALID_HTTP_RESPONSE: set = {200}

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
