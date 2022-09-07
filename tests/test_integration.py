"""Integration tests that require Porkbun API communication
WARNING: THESE TESTS WILL WRITE, READ, DELETE AND MODIFY DNS RECORDS
ONLY RUN THESE TESTS AGAINST A DOMAIN THAT IS PREPARED FOR THESE CHANGES
"""
import unittest
from unittest.mock import patch
from os import getenv
from httpx import ReadTimeout

try:
    from dotenv import load_dotenv
    load_dotenv()
except ModuleNotFoundError:
    pass

import pyrkbun
from pyrkbun import ApiError, ApiFailure


# These constants enable you to customise which test suites to run
# Set applicable environment variables to control test suite execution
TEST_DOMAIN_NAME: str = getenv('PYRK_TEST_DOMAIN_NAME')
TEST_PING: str = getenv('PYRK_TEST_PING')
TEST_PRICING: str = getenv('PYRK_TEST_PRICING')
TEST_SSL: str = getenv('PYRK_TEST_SSL')
TEST_DNS_TLSA: str = getenv('PYRK_TEST_DNS_TLSA')
TEST_DNS_RETRIEVE: str = getenv('PYRK_TEST_DNS_RETRIEVE')
TEST_DNS_CREATE: str = getenv('PYRK_TEST_DNS_CREATE')
TEST_DNS_DELETE: str = getenv('PYRK_TEST_DNS_DELETE')
TEST_DNS_MODIFY: str = getenv('PYRK_TEST_DNS_MODIFY')


@unittest.skipUnless(TEST_PING, 'PYRK_TEST_PING env not set, skipping')
class ApiPingIntegrationTests(unittest.TestCase):
    """Test API ping operation
    """

    def test_api_ping_v4_v6(self):
        """Test API ping using the v4/v6 API host
        """
        ping: dict = pyrkbun.ping()
        self.assertIsInstance(ping, dict)
        self.assertEqual(ping['status'], 'SUCCESS')
        self.assertTrue(len(ping['yourIp']) >= 7)

    # Need to patch the base url to force use of v4 host
    @patch('pyrkbun.util.BASE_URL', 'https://api-ipv4.porkbun.com/api/json/v3')
    def test_api_ping_v4_only_implicit(self):
        """Test API ping using the v4 only API host inherited from environ
        """
        ping: dict = pyrkbun.ping()
        ip_add: str = ping['yourIp']
        self.assertIsInstance(ping, dict)
        self.assertEqual(ping['status'], 'SUCCESS')
        self.assertEqual(len(ip_add.split('.')), 4)

    def test_api_ping_v4_only_explicit(self):
        """Test API ping using the v4 only API via explicit setting
        """
        ping: dict = pyrkbun.ping(ipv4=True)
        ip_add: str = ping['yourIp']
        self.assertIsInstance(ping, dict)
        self.assertEqual(ping['status'], 'SUCCESS')
        self.assertEqual(len(ip_add.split('.')), 4)


@unittest.skipUnless(TEST_PRICING, 'PYRK_TEST_PRICING env not set, skipping')
class PricingIntegrationTests(unittest.TestCase):
    """Test pricing API
    """

    def test_pricing_get(self):
        """Validate data returned from pricing API
        """
        pricing: dict = pyrkbun.pricing.get()
        price_data: dict = pricing['pricing']
        self.assertIsInstance(pricing, dict)
        self.assertEqual(pricing['status'], 'SUCCESS')
        self.assertIn('com', price_data.keys())
        self.assertIn('net', price_data.keys())
        self.assertIn('org', price_data.keys())


@unittest.skipUnless(TEST_SSL, 'PYRK_TEST_SSL env not set, skipping')
class SslIntegrationTests(unittest.TestCase):
    """Test SSL API
    WARNING: This test suite will retirieve private certificate data for your domain
    If the SSL cert is not available for this domian the test will be auto skipped
    """

    def test_ssl_get(self):
        """Validate data returned from SSL API
        """
        try:
            ssl: dict = pyrkbun.ssl.get(TEST_DOMAIN_NAME)
        except ApiError as error:
            if error.message == 'The SSL certificate is not ready for this domain.':
                self.skipTest('Skipping test as domain does not hold ssl cert')

        cert_int: str = ssl["intermediatecertificate"][0:27]
        cert_chain: str = ssl["certificatechain"][0:27]
        cert_private: str = ssl["privatekey"][0:27]
        cert_public: str = ssl["publickey"][0:26]
        self.assertIsInstance(ssl, dict)
        self.assertEqual(ssl['status'], 'SUCCESS')
        self.assertEqual(cert_int, '-----BEGIN CERTIFICATE-----')
        self.assertEqual(cert_chain, '-----BEGIN CERTIFICATE-----')
        self.assertEqual(cert_private, '-----BEGIN PRIVATE KEY-----')
        self.assertEqual(cert_public, '-----BEGIN PUBLIC KEY-----')


@unittest.skipUnless(TEST_DNS_RETRIEVE, 'PYRK_TEST_DNS_RETRIEVE env not set, skipping')
class DnsRetrievalIntegrationTests(unittest.TestCase):
    """Test DNS API for record retrival
    WARNING: This test suite WILL MODIFY your DOMAIN RECORDS
    All records created SHOULD be automatically REMOVED on test completion
    """

    @classmethod
    def setUpClass(cls) -> None:
        """Setup test records
        """
        test_records = [{'name': 'pyrkbuntesta',
                         'type': 'A',
                         'content': '198.51.100.45',
                         'ttl': '600',
                         'prio': '0',
                         'notes': 'pyrkbun test A record'},
                        {'name': 'pyrkbuntestaaaa',
                         'type': 'AAAA',
                         'content': '2001:0db8:85a3:0000:0000:8a2e:0370:7334',
                         'ttl': '600',
                         'prio': '0',
                         'notes': 'pyrkbun test AAAA record'},
                        {'name': '',
                         'type': 'MX',
                         'content': f'pyrkbuntesta.{TEST_DOMAIN_NAME}',
                         'ttl': '600',
                         'prio': '65534',
                         'notes': 'pyrkbun test MX record 1'},
                        {'name': '',
                         'type': 'MX',
                         'content': f'pyrkbuntestaaaa.{TEST_DOMAIN_NAME}',
                         'ttl': '600',
                         'prio': '65533',
                         'notes': 'pyrkbun test MX record 2'},]
        cls.test_records = []
        for record in test_records:
            create = pyrkbun.dns.create_record(TEST_DOMAIN_NAME, record)
            test_data = {'id': str(create['id']), 'name': record['name'], 'type': record['type']}
            cls.test_records.append(test_data)

    @classmethod
    def tearDownClass(cls) -> None:
        """Cleanup test records
        """
        for record in cls.test_records:
            pyrkbun.dns.delete_record(TEST_DOMAIN_NAME, record_id=record['id'])

    def test_get_records_all(self):
        """Test retrival of all records from a domain using class method
        """
        dns_records = pyrkbun.dns.get_records(TEST_DOMAIN_NAME)
        a_count = 0
        aaaa_count = 0
        mx_count = 0
        for record in dns_records:
            self.assertIsInstance(record, pyrkbun.dns)
            if record.record_type == 'A' and record.name == 'pyrkbuntesta':
                a_count += 1
            elif record.record_type == 'AAAA' and record.name == 'pyrkbuntestaaaa':
                aaaa_count += 1
            elif record.record_type == 'MX' and record.content[0:11] == 'pyrkbuntest':
                mx_count += 1
        self.assertEqual(a_count, 1)
        self.assertEqual(aaaa_count, 1)
        self.assertEqual(mx_count, 2)

    def test_get_records_by_type(self):
        """Test retrival of all records by type using class method
        """
        dns_records = pyrkbun.dns.get_records(TEST_DOMAIN_NAME, record_type='MX')
        dns_records = [record for record in dns_records if record.content[0:11] == 'pyrkbuntest']
        self.assertEqual(len(dns_records), 2)
        for record in dns_records:
            self.assertIsInstance(record, pyrkbun.dns)
            self.assertEqual('MX', record.record_type)

    def test_get_records_by_type_and_name(self):
        """Test retrival by type and name using class method
        """
        dns_records = pyrkbun.dns.get_records(TEST_DOMAIN_NAME, record_type='A', \
            name='pyrkbuntesta')
        target_record = dns_records[0]
        self.assertEqual(len(dns_records), 1)
        self.assertIsInstance(target_record, pyrkbun.dns)
        self.assertEqual('pyrkbuntesta', target_record.name)
        self.assertEqual('A', target_record.record_type)

    def test_get_records_by_id(self):
        """Test retrival of records by id using class method
        """
        for test_record in self.test_records:
            dns_records = pyrkbun.dns.get_records(TEST_DOMAIN_NAME, record_id=test_record['id'])
            target_record = dns_records[0]
            self.assertEqual(len(dns_records), 1)
            self.assertIsInstance(target_record, pyrkbun.dns)
            self.assertEqual(test_record['id'], target_record.record_id)
            self.assertEqual(test_record['name'], target_record.name)
            self.assertEqual(test_record['type'], target_record.record_type)

    def test_record_refresh(self):
        """Test record refresh instance method
        """
        test_record = [record for record in self.test_records if record['type'] == 'AAAA'][0]
        target_record = pyrkbun.dns(TEST_DOMAIN_NAME, 'A', 'BAR', record_id=test_record['id'])
        target_record.refresh()
        self.assertIsInstance(target_record, pyrkbun.dns)
        self.assertEqual(test_record['id'], target_record.record_id)
        self.assertEqual(test_record['name'], target_record.name)
        self.assertEqual(test_record['type'], target_record.record_type)
        self.assertEqual('2001:0db8:85a3:0000:0000:8a2e:0370:7334', target_record.content)


@unittest.skipUnless(TEST_DNS_CREATE, 'PYRK_TEST_DNS_CREATE env not set, skipping')
class DnsCreateIntegrationTests(unittest.TestCase):
    """Test DNS API for record creation
    WARNING: This test suite WILL MODIFY your DOMAIN RECORDS
    WARNING: This test suite WILL CREATE a CAA record permitting certifcate
    issuance by a CA provider named pyrkbuntest.{TEST_DOMAIN_NAME}
    All records created SHOULD be automatically REMOVED on test completion
    """

    @classmethod
    def setUpClass(cls) -> None:
        """Define test record data and store in cls attribute
        """
        cls.test_data = {'A': {'name': 'pyrkbuncreatea',
                               'record_type': 'A',
                               'content': '198.51.100.45',
                               'ttl': '600',
                               'prio': '0',
                               'notes': 'pyrkbun test A record',
                               'domain': TEST_DOMAIN_NAME},
                         'AAAA': {'name': 'pyrkbuncreateaaaa',
                                  'record_type': 'AAAA',
                                  'content': '2001:0db8:85a3:0000:0000:8a2e:0370:7334',
                                  'ttl': '600',
                                  'prio': '0',
                                  'notes': 'pyrkbun test AAAA record',
                                  'domain': TEST_DOMAIN_NAME},
                         'MX': {'name': '',
                                'record_type': 'MX',
                                'content': 'pyrkbuncreatemx.example.com',
                                'ttl': '600',
                                'prio': '65534',
                                'notes': 'pyrkbun test MX record',
                                'domain': TEST_DOMAIN_NAME},
                         'CNAME': {'name': 'pyrkbuncreatecname',
                                   'record_type': 'CNAME',
                                   'content': 'www.example.com',
                                   'ttl': '600',
                                   'prio': '0',
                                   'notes': 'pyrkbun test CNAME record',
                                   'domain': TEST_DOMAIN_NAME},
                         'ALIAS': {'name': 'pyrkbuncreatealias',
                                   'record_type': 'ALIAS',
                                   'content': 'www.example.org',
                                   'ttl': '600',
                                   'prio': '0',
                                   'notes': 'pyrkbun test ALIAS record',
                                   'domain': TEST_DOMAIN_NAME},
                         'TXT': {'name': '',
                                 'record_type': 'TXT',
                                 'content': 'txt api create record test',
                                 'ttl': '600',
                                 'prio': '0',
                                 'notes': 'pyrkbun test TXT record',
                                 'domain': TEST_DOMAIN_NAME},
                         'NS': {'name': f'pyrkbuncreatesubdomain.{TEST_DOMAIN_NAME}',
                                'record_type': 'NS',
                                'content': f'pyrkbuncreatens.{TEST_DOMAIN_NAME}',
                                'ttl': '600',
                                'prio': '0',
                                'notes': 'pyrkbun test NS record',
                                'domain': TEST_DOMAIN_NAME},
                         'SRV': {'name': '_pyrk._bun',
                                 'record_type': 'SRV',
                                 'content': f'65533 65532 pyrkbuncreatesrv.{TEST_DOMAIN_NAME}',
                                 'prio': '65533',
                                 'notes': 'pyrkbun test SRV record',
                                 'domain': TEST_DOMAIN_NAME},
                         'TLSA': {'name': '_443._tcp.pyrkbuncreate',
                                  'record_type': 'TLSA',
                                  'content': '0 0 0 123456789abcdef123456789abcdef',
                                  'ttl': '600',
                                  'prio': '0',
                                  'notes': 'pyrkbun test TLSA record',
                                  'domain': TEST_DOMAIN_NAME},
                         'CAA': {'name': '',
                                 'record_type': 'CAA',
                                 'content': f'0 issue "pyrkbuncreate.{TEST_DOMAIN_NAME}"',
                                 'ttl': '600',
                                 'prio': '0',
                                 'notes': 'pyrkbun test CAA record',
                                 'domain': TEST_DOMAIN_NAME}}
        # This will hold ID's of succesfully created records
        cls.created_record_ids = []

    @classmethod
    def tearDownClass(cls) -> None:
        """Clean-up test records created during testing
        """
        for record_id in cls.created_record_ids:
            try:
                pyrkbun.dns.delete_record(TEST_DOMAIN_NAME, record_id=record_id)
            except (ApiError, ApiFailure, ReadTimeout) as error:
                print(error.message)
                
    def test_create_a_record(self):
        """Test creation of A record
        """
        config: dict = self.test_data['A']
        dns_record = pyrkbun.dns(**config)
        result: dict = dns_record.create()
        if dns_record.record_id:
            self.created_record_ids.append(dns_record.record_id)
        self.assertTrue(dns_record.record_id)
        self.assertEqual('SUCCESS', result['status'])
        self.assertIn(str(result['id']), self.created_record_ids)

    def test_create_aaaa_record(self):
        """Test creation of AAAA record
        """
        config: dict = self.test_data['AAAA']
        dns_record = pyrkbun.dns(**config)
        result: dict = dns_record.create()
        if dns_record.record_id:
            self.created_record_ids.append(dns_record.record_id)
        self.assertTrue(dns_record.record_id)
        self.assertEqual('SUCCESS', result['status'])
        self.assertIn(str(result['id']), self.created_record_ids)

    def test_create_mx_record(self):
        """Test creation of MX record
        """
        config: dict = self.test_data['MX']
        dns_record = pyrkbun.dns(**config)
        result: dict = dns_record.create()
        if dns_record.record_id:
            self.created_record_ids.append(dns_record.record_id)
        self.assertTrue(dns_record.record_id)
        self.assertEqual('SUCCESS', result['status'])
        self.assertIn(str(result['id']), self.created_record_ids)

    def test_create_cname_record(self):
        """Test creation of CNAME record
        """
        config: dict = self.test_data['CNAME']
        dns_record = pyrkbun.dns(**config)
        result: dict = dns_record.create()
        if dns_record.record_id:
            self.created_record_ids.append(dns_record.record_id)
        self.assertTrue(dns_record.record_id)
        self.assertEqual('SUCCESS', result['status'])
        self.assertIn(str(result['id']), self.created_record_ids)

    def test_create_alias_record(self):
        """Test creation of ALIAS record
        """
        config: dict = self.test_data['ALIAS']
        dns_record = pyrkbun.dns(**config)
        result: dict = dns_record.create()
        if dns_record.record_id:
            self.created_record_ids.append(dns_record.record_id)
        self.assertTrue(dns_record.record_id)
        self.assertEqual('SUCCESS', result['status'])
        self.assertIn(str(result['id']), self.created_record_ids)

    def test_create_txt_record(self):
        """Test creation of TXT record
        """
        config: dict = self.test_data['TXT']
        dns_record = pyrkbun.dns(**config)
        result: dict = dns_record.create()
        if dns_record.record_id:
            self.created_record_ids.append(dns_record.record_id)
        self.assertTrue(dns_record.record_id)
        self.assertEqual('SUCCESS', result['status'])
        self.assertIn(str(result['id']), self.created_record_ids)

    def test_create_ns_record(self):
        """Test creation of NS record
        """
        config: dict = self.test_data['NS']
        dns_record = pyrkbun.dns(**config)
        result: dict = dns_record.create()
        if dns_record.record_id:
            self.created_record_ids.append(dns_record.record_id)
        self.assertTrue(dns_record.record_id)
        self.assertEqual('SUCCESS', result['status'])
        self.assertIn(str(result['id']), self.created_record_ids)

    def test_create_srv_record(self):
        """Test creation of SRV record
        """
        config: dict = self.test_data['SRV']
        dns_record = pyrkbun.dns(**config)
        result: dict = dns_record.create()
        if dns_record.record_id:
            self.created_record_ids.append(dns_record.record_id)
        self.assertTrue(dns_record.record_id)
        self.assertEqual('SUCCESS', result['status'])
        self.assertIn(str(result['id']), self.created_record_ids)

    # Having trouble with TLSA record creation - may require DNSSEC be enabled
    # TODO: Check requirements for TLSA record creation
    @unittest.skipUnless(TEST_DNS_TLSA, 'PYRK_TEST_DNS_TLSA env not set, skipping')
    def test_create_tlsa_record(self):
        """Test creation of TLSA record
        """
        config: dict = self.test_data['TLSA']
        dns_record = pyrkbun.dns(**config)
        result: dict = dns_record.create()
        if dns_record.record_id:
            self.created_record_ids.append(dns_record.record_id)
        self.assertTrue(dns_record.record_id)
        self.assertEqual('SUCCESS', result['status'])
        self.assertIn(str(result['id']), self.created_record_ids)

    def test_create_caa_record(self):
        """Test creation of CAA record
        """
        config: dict = self.test_data['CAA']
        dns_record = pyrkbun.dns(**config)
        result: dict = dns_record.create()
        if dns_record.record_id:
            self.created_record_ids.append(dns_record.record_id)
        self.assertTrue(dns_record.record_id)
        self.assertEqual('SUCCESS', result['status'])
        self.assertIn(str(result['id']), self.created_record_ids)

    def test_create_a_record_with_class_method(self):
        """Test creation of A record using class method
        """
        record = {'name': 'pyrkbuntestacmethod',
                  'type': 'A',
                  'content': '198.51.100.46',
                  'ttl': '660',
                  'notes': 'Pyrkbun test A record with class method'}
        result = pyrkbun.dns.create_record(TEST_DOMAIN_NAME, record)
        if result['id']:
            self.created_record_ids.append(str(result['id']))
        self.assertTrue(result['id'])
        self.assertEqual('SUCCESS', result['status'])
        self.assertIn(str(result['id']), self.created_record_ids)


@unittest.skipUnless(TEST_DNS_DELETE, 'PYRK_TEST_DNS_DELETE env not set, skipping')
class DnsDeleteIntegrationTests(unittest.TestCase):
    """Test DNS API for record deletion
    WARNING: This test suite WILL MODIFY your DOMAIN RECORDS
    All records created SHOULD be automatically REMOVED on test completion
    """

    @classmethod
    def setUpClass(cls) -> None:
        """Setup test records
        """
        test_records = [{'name': 'pyrkbuntesta',
                         'type': 'A',
                         'content': '198.51.100.45',
                         'ttl': '600',
                         'prio': '0',
                         'notes': 'pyrkbun test A record'},
                        {'name': 'pyrkbuntestaaaa',
                         'type': 'AAAA',
                         'content': '2001:0db8:85a3:0000:0000:8a2e:0370:7334',
                         'ttl': '600',
                         'prio': '0',
                         'notes': 'pyrkbun test AAAA record'},
                        {'name': '',
                         'type': 'MX',
                         'content': f'pyrkbuntesta.{TEST_DOMAIN_NAME}',
                         'ttl': '600',
                         'prio': '65534',
                         'notes': 'pyrkbun test MX record'}]
        cls.test_records = []
        for record in test_records:
            create = pyrkbun.dns.create_record(TEST_DOMAIN_NAME, record)
            test_data = {'id': str(create['id']), 'name': record['name'], 'type': record['type']}
            cls.test_records.append(test_data)

    @classmethod
    def tearDownClass(cls) -> None:
        """Cleanup test records if any remain
        """
        for record in cls.test_records:
            try:
                pyrkbun.dns.delete_record(TEST_DOMAIN_NAME, record_id=record['id'])
            except ApiError as error:
                if error.message == "Invalid record ID.":
                    pass

    def test_delete_by_id_class_method(self):
        """Test deletion of record by id using class method
        """
        record = [record for record in self.test_records if record['type'] == 'A'][0]
        result = pyrkbun.dns.delete_record(TEST_DOMAIN_NAME, record_id = record['id'])
        check = pyrkbun.dns.get_records(TEST_DOMAIN_NAME, record_id = record['id'])
        self.assertEqual('SUCCESS', result['status'])
        self.assertListEqual(check, [])

    def test_delete_by_name_type_class_method(self):
        """Test deletion of record by name and type using class method
        """
        record = [record for record in self.test_records if record['type'] == 'AAAA'][0]
        result = pyrkbun.dns.delete_record(TEST_DOMAIN_NAME, record['type'], record['name'])
        check = pyrkbun.dns.get_records(TEST_DOMAIN_NAME, record_id = record['id'])
        self.assertEqual('SUCCESS', result['status'])
        self.assertListEqual(check, [])

    def test_delete_by_instance_method(self):
        """Test deletion of record using class instance method
        """
        record = [record for record in self.test_records if record['type'] == 'MX'][0]
        retrieved_record = pyrkbun.dns.get_records(TEST_DOMAIN_NAME, record_id = record['id'])[0]
        result = retrieved_record.delete()
        check = pyrkbun.dns.get_records(TEST_DOMAIN_NAME, record_id = record['id'])
        self.assertEqual('SUCCESS', result['status'])
        self.assertListEqual(check, [])


@unittest.skipUnless(TEST_DNS_MODIFY, 'PYRK_TEST_DNS_MODIFY env not set, skipping')
class DnsModifyIntegrationTests(unittest.TestCase):
    """Test DNS API for record modification
    WARNING: This test suite WILL MODIFY your DOMAIN RECORDS
    All records created SHOULD be automatically REMOVED on test completion
    """

    @classmethod
    def setUpClass(cls) -> None:
        """Create test records
        """
        test_records = [{'name': 'pyrkbuntesta',
                         'type': 'A',
                         'content': '198.51.100.45',
                         'ttl': '600',
                         'prio': '0',
                         'notes': 'pyrkbun test A record'},
                        {'name': 'pyrkbuntestaaaa',
                         'type': 'AAAA',
                         'content': '2001:0db8:85a3:0000:0000:8a2e:0370:7334',
                         'ttl': '600',
                         'prio': '0',
                         'notes': 'pyrkbun test AAAA record'},
                        {'name': 'pyrkbuntestcname',
                         'type': 'CNAME',
                         'content': f'pyrkbuntestaaaa.{TEST_DOMAIN_NAME}',
                         'ttl': '600',
                         'prio': '0',
                         'notes': 'pyrkbun test CNAME record'}]
        cls.test_records = []
        for record in test_records:
            create = pyrkbun.dns.create_record(TEST_DOMAIN_NAME, record)
            test_data = {'id': str(create['id']), 'name': record['name'], 'type': record['type']}
            cls.test_records.append(test_data)

    @classmethod
    def tearDownClass(cls) -> None:
        """Delete test records
        """
        for record in cls.test_records:
            try:
                pyrkbun.dns.delete_record(TEST_DOMAIN_NAME, record_id=record['id'])
            except ApiError as error:
                if error.message == "Invalid record ID.":
                    pass

    def test_edit_by_id_class_method(self):
        """Test edit of record by id using class method
        """
        record = [record for record in self.test_records if record['type'] == 'A'][0]
        updates = {'name': 'pyrkbuntestaedit',
                   'type': 'A',
                   'content': '198.51.100.55',
                   'ttl': '680',
                   'prio': '0',
                   'notes': 'pyrkbun test A record'}
        result = pyrkbun.dns.edit_record(TEST_DOMAIN_NAME, updates, record_id = record['id'])
        check = pyrkbun.dns.get_records(TEST_DOMAIN_NAME, record_id = record['id'])[0]
        self.assertEqual('SUCCESS', result['status'])
        self.assertEqual('pyrkbuntestaedit', check.name)
        self.assertEqual('198.51.100.55', check.content)
        self.assertEqual('680', check.ttl)

    def test_edit_by_name_type_class_method(self):
        """Test edit of record by type and name using class method
        """
        record = [record for record in self.test_records if record['type'] == 'AAAA'][0]
        updates = {'name': 'pyrkbuntestaaaa',
                   'type': 'AAAA',
                   'content': '2001:0db8:85a3:0000:0000:8a2e:0370:adef',
                   'ttl': '700',
                   'prio': '0',
                   'notes': 'pyrkbun test A record'}
        result = pyrkbun.dns.edit_record(TEST_DOMAIN_NAME, updates, record['type'], record['name'])
        check = pyrkbun.dns.get_records(TEST_DOMAIN_NAME, record_id = record['id'])[0]
        self.assertEqual('SUCCESS', result['status'])
        self.assertEqual('pyrkbuntestaaaa', check.name)
        self.assertEqual('2001:0db8:85a3:0000:0000:8a2e:0370:adef', check.content)
        self.assertEqual('700', check.ttl)

    def test_edit_by_instance_method(self):
        """Test edit of record by using instance method
        """
        record = [record for record in self.test_records if record['type'] == 'CNAME'][0]
        retrieved_record = pyrkbun.dns.get_records(TEST_DOMAIN_NAME, record_id = record['id'])[0]
        retrieved_record.name = 'pyrkbuntestcnameedit'
        retrieved_record.content = f'pyrkbuntesta.{TEST_DOMAIN_NAME}'
        retrieved_record.ttl = '770'
        result = retrieved_record.update()
        check = pyrkbun.dns.get_records(TEST_DOMAIN_NAME, record_id = record['id'])[0]
        self.assertEqual('SUCCESS', result['status'])
        self.assertEqual('pyrkbuntestcnameedit', check.name)
        self.assertEqual(f'pyrkbuntesta.{TEST_DOMAIN_NAME}', check.content)
        self.assertEqual('770', check.ttl)

if __name__ == '__main__':
    unittest.main()
