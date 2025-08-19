"""Integration tests that require Porkbun API communication
WARNING: THESE TESTS WILL WRITE, READ, DELETE AND MODIFY DNS RECORDS
ONLY RUN THESE TESTS AGAINST A DOMAIN THAT IS PREPARED FOR THESE CHANGES
"""
import unittest
from unittest import skipUnless
from os import getenv
from httpx import ReadTimeout

try:
    from dotenv import load_dotenv
    load_dotenv()
except ModuleNotFoundError:
    pass

from pyrkbun.client import PyrkbunClient, ApiError, ApiFailure
from pyrkbun.dns import Dns
from pyrkbun.ssl import Ssl
from pyrkbun.pricing import Pricing

TEST_DOMAIN_NAME = getenv("TEST_DOMAIN_NAME","")

@skipUnless(TEST_DOMAIN_NAME != "", "No test domain configured.")
class ApiPingIntegrationTests(unittest.TestCase):
    """Test API ping operation
    """

    def test_api_ping_v4_v6(self):
        """Test API ping using the v4/v6 API host
        """
        client = PyrkbunClient.build(read_env=True)
        ping: dict = client.ping()
        self.assertIsInstance(ping, dict)
        self.assertEqual(ping['status'], 'SUCCESS')
        self.assertTrue(len(ping['yourIp']) >= 7)

    def test_api_ping_v4_only_implicit(self):
        """Test API ping using the v4 only API host via client config
        """
        client = PyrkbunClient.build(read_env=True, force_v4=True)
        ping: dict = client.ping()
        ip_add: str = ping['yourIp']
        self.assertIsInstance(ping, dict)
        self.assertEqual(ping['status'], 'SUCCESS')
        self.assertEqual(len(ip_add.split('.')), 4)

    def test_api_ping_v4_only_explicit(self):
        """Test API ping using the v4 only API via explicit setting
        """
        client = PyrkbunClient.build(read_env=True)
        ping: dict = client.ping(ipv4=True)
        ip_add: str = ping['yourIp']
        self.assertIsInstance(ping, dict)
        self.assertEqual(ping['status'], 'SUCCESS')
        self.assertEqual(len(ip_add.split('.')), 4)

@skipUnless(TEST_DOMAIN_NAME != "", "No test domain configured.")
class PricingIntegrationTests(unittest.TestCase):
    """Test pricing API
    """

    def test_pricing_get(self):
        """Validate data returned from pricing API
        """
        client = PyrkbunClient.build(read_env=True, timeout=30)
        pricing_api = Pricing(client)
        pricing = pricing_api.get()
        self.assertIsInstance(pricing.pricing, dict)
        self.assertIn('com', pricing.pricing.keys())
        self.assertIn('net', pricing.pricing.keys())
        self.assertIn('org', pricing.pricing.keys())

@skipUnless(TEST_DOMAIN_NAME != "", "No test domain configured.")
class SslIntegrationTests(unittest.TestCase):
    """Test SSL API
    WARNING: This test suite will retirieve private certificate data for your domain
    If the SSL cert is not available for this domian the test will be auto skipped
    """

    def test_ssl_get(self):
        """Validate data returned from SSL API
        """
        try:
            client = PyrkbunClient.build(read_env=True)
            ssl_api = Ssl(client)
            ssl = ssl_api.get(TEST_DOMAIN_NAME)
        except ApiError as error:
            if error.message == 'The SSL certificate is not ready for this domain.':
                self.skipTest('Skipping test as domain does not hold ssl cert')
            return

        cert_int: str = ssl.intermediatecertificate[0:27]
        cert_chain: str = ssl.certificatechain[0:27]
        cert_private: str = ssl.privatekey[0:27]
        cert_public: str = ssl.publickey[0:26]
        self.assertEqual(cert_int, '-----BEGIN CERTIFICATE-----')
        self.assertEqual(cert_chain, '-----BEGIN CERTIFICATE-----')
        self.assertEqual(cert_private, '-----BEGIN PRIVATE KEY-----')
        self.assertEqual(cert_public, '-----BEGIN PUBLIC KEY-----')

@skipUnless(TEST_DOMAIN_NAME != "", "No test domain configured.")
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
        client = PyrkbunClient.build()
        dns_api = Dns(client)
        for record in test_records:
            create = dns_api.create_record(
                TEST_DOMAIN_NAME,
                record['type'],
                record['content'],
                name=record['name'],
                ttl=record['ttl'],
                prio=record['prio'],
                notes=record['notes']
            )
            test_data = {'id': str(create.id), 'name': record['name'], 'type': record['type']}
            cls.test_records.append(test_data)

    @classmethod
    def tearDownClass(cls) -> None:
        """Cleanup test records
        """
        client = PyrkbunClient.build()
        dns_api = Dns(client)
        for record in cls.test_records:
            dns_api.delete_record(TEST_DOMAIN_NAME, record_id=record['id'])

    def test_get_records_all(self):
        """Test retrival of all records from a domain using class method
        """
        client = PyrkbunClient.build()
        dns_api = Dns(client)
        dns_records = dns_api.get_records(TEST_DOMAIN_NAME)
        a_count = 0
        aaaa_count = 0
        mx_count = 0
        for record in dns_records.records:
            if record.type == 'A' and record.name == 'pyrkbuntesta':
                a_count += 1
            elif record.type == 'AAAA' and record.name == 'pyrkbuntestaaaa':
                aaaa_count += 1
            elif record.type == 'MX' and record.content[0:11] == 'pyrkbuntest':
                mx_count += 1
        self.assertEqual(a_count, 1)
        self.assertEqual(aaaa_count, 1)
        self.assertEqual(mx_count, 2)

    def test_get_records_by_type(self):
        """Test retrival of all records by type using class method
        """
        client = PyrkbunClient.build()
        dns_api = Dns(client)
        dns_response = dns_api.get_records(TEST_DOMAIN_NAME, record_type='MX')
        dns_records = [record for record in dns_response.records if record.content[0:11] == 'pyrkbuntest']
        self.assertEqual(len(dns_records), 2)
        for record in dns_records:
            self.assertIsInstance(record, type(dns_response.records[0]))
            self.assertEqual('MX', record.type)

    def test_get_records_by_type_and_name(self):
        """Test retrival by type and name using class method
        """
        client = PyrkbunClient.build()
        dns_api = Dns(client)
        dns_response = dns_api.get_records(TEST_DOMAIN_NAME, record_type='A', \
            name='pyrkbuntesta')
        target_record = dns_response.records[0]
        self.assertEqual(len(dns_response.records), 1)
        self.assertIsInstance(target_record, type(dns_response.records[0]))
        self.assertEqual('pyrkbuntesta', target_record.name)
        self.assertEqual('A', target_record.type)

    def test_get_records_by_id(self):
        """Test retrival of records by id using class method
        """
        client = PyrkbunClient.build()
        dns_api = Dns(client)
        for test_record in self.test_records:
            dns_response = dns_api.get_records(TEST_DOMAIN_NAME, record_id=test_record['id'])
            target_record = dns_response.records[0]
            self.assertEqual(len(dns_response.records), 1)
            self.assertIsInstance(target_record, type(dns_response.records[0]))
            self.assertEqual(test_record['id'], target_record.id)
            self.assertEqual(test_record['name'], target_record.name)
            self.assertEqual(test_record['type'], target_record.type)

    def test_record_refresh(self):
        """Test record refresh functionality using new API
        """
        client = PyrkbunClient.build()
        dns_api = Dns(client)
        test_record = [record for record in self.test_records if record['type'] == 'AAAA'][0]
        # Get the current record by ID
        dns_response = dns_api.get_records(TEST_DOMAIN_NAME, record_id=test_record['id'])
        target_record = dns_response.records[0]
        self.assertIsInstance(target_record, type(dns_response.records[0]))
        self.assertEqual(test_record['id'], target_record.id)
        self.assertEqual(test_record['name'], target_record.name)
        self.assertEqual(test_record['type'], target_record.type)
        self.assertEqual('2001:0db8:85a3:0000:0000:8a2e:0370:7334', target_record.content)

@skipUnless(TEST_DOMAIN_NAME != "", "No test domain configured.")
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
        client = PyrkbunClient.build()
        dns_api = Dns(client)
        for record_id in cls.created_record_ids:
            try:
                dns_api.delete_record(TEST_DOMAIN_NAME, record_id=record_id)
            except (ApiError, ApiFailure, ReadTimeout) as error:
                print(str(error))
                
    def test_create_a_record(self):
        """Test creation of A record
        """
        client = PyrkbunClient.build()
        dns_api = Dns(client)
        config: dict = self.test_data['A']
        dns_record = dns_api.create_record(
            config['domain'],
            config['record_type'],
            config['content'],
            name=config['name'],
            ttl=config['ttl'],
            prio=config['prio'],
            notes=config['notes']
        )
        self.created_record_ids.append(dns_record.id)
        self.assertTrue(dns_record.id)
        self.assertEqual(config['name'], dns_record.name)
        self.assertEqual(config['record_type'], dns_record.type)

    def test_create_aaaa_record(self):
        """Test creation of AAAA record
        """
        client = PyrkbunClient.build()
        dns_api = Dns(client)
        config: dict = self.test_data['AAAA']
        dns_record = dns_api.create_record(
            config['domain'],
            config['record_type'],
            config['content'],
            name=config['name'],
            ttl=config['ttl'],
            prio=config['prio'],
            notes=config['notes']
        )
        self.created_record_ids.append(dns_record.id)
        self.assertTrue(dns_record.id)
        self.assertEqual(config['name'], dns_record.name)
        self.assertEqual(config['record_type'], dns_record.type)

    def test_create_mx_record(self):
        """Test creation of MX record
        """
        client = PyrkbunClient.build()
        dns_api = Dns(client)
        config: dict = self.test_data['MX']
        dns_record = dns_api.create_record(
            config['domain'],
            config['record_type'],
            config['content'],
            name=config['name'],
            ttl=config['ttl'],
            prio=config['prio'],
            notes=config['notes']
        )
        self.created_record_ids.append(dns_record.id)
        self.assertTrue(dns_record.id)
        self.assertEqual(config['name'], dns_record.name)
        self.assertEqual(config['record_type'], dns_record.type)

    def test_create_cname_record(self):
        """Test creation of CNAME record
        """
        client = PyrkbunClient.build()
        dns_api = Dns(client)
        config: dict = self.test_data['CNAME']
        dns_record = dns_api.create_record(
            config['domain'],
            config['record_type'],
            config['content'],
            name=config['name'],
            ttl=config['ttl'],
            prio=config['prio'],
            notes=config['notes']
        )
        self.created_record_ids.append(dns_record.id)
        self.assertTrue(dns_record.id)
        self.assertEqual(config['name'], dns_record.name)
        self.assertEqual(config['record_type'], dns_record.type)

    def test_create_alias_record(self):
        """Test creation of ALIAS record
        """
        client = PyrkbunClient.build()
        dns_api = Dns(client)
        config: dict = self.test_data['ALIAS']
        dns_record = dns_api.create_record(
            config['domain'],
            config['record_type'],
            config['content'],
            name=config['name'],
            ttl=config['ttl'],
            prio=config['prio'],
            notes=config['notes']
        )
        self.created_record_ids.append(dns_record.id)
        self.assertTrue(dns_record.id)
        self.assertEqual(config['name'], dns_record.name)
        self.assertEqual(config['record_type'], dns_record.type)

    def test_create_txt_record(self):
        """Test creation of TXT record
        """
        client = PyrkbunClient.build()
        dns_api = Dns(client)
        config: dict = self.test_data['TXT']
        dns_record = dns_api.create_record(
            config['domain'],
            config['record_type'],
            config['content'],
            name=config['name'],
            ttl=config['ttl'],
            prio=config['prio'],
            notes=config['notes']
        )
        self.created_record_ids.append(dns_record.id)
        self.assertTrue(dns_record.id)
        self.assertEqual(config['name'], dns_record.name)
        self.assertEqual(config['record_type'], dns_record.type)

    def test_create_ns_record(self):
        """Test creation of NS record
        """
        client = PyrkbunClient.build()
        dns_api = Dns(client)
        config: dict = self.test_data['NS']
        dns_record = dns_api.create_record(
            config['domain'],
            config['record_type'],
            config['content'],
            name=config['name'],
            ttl=config['ttl'],
            prio=config['prio'],
            notes=config['notes']
        )
        self.created_record_ids.append(dns_record.id)
        self.assertTrue(dns_record.id)
        self.assertEqual(config['name'], dns_record.name)
        self.assertEqual(config['record_type'], dns_record.type)

    def test_create_srv_record(self):
        """Test creation of SRV record
        """
        client = PyrkbunClient.build()
        dns_api = Dns(client)
        config: dict = self.test_data['SRV']
        dns_record = dns_api.create_record(
            config['domain'],
            config['record_type'],
            config['content'],
            name=config['name'],
            prio=config['prio'],
            notes=config['notes']
        )
        self.created_record_ids.append(dns_record.id)
        self.assertTrue(dns_record.id)
        self.assertEqual(config['name'], dns_record.name)
        self.assertEqual(config['record_type'], dns_record.type)

    def test_create_tlsa_record(self):
        """Test creation of TLSA record
        """
        client = PyrkbunClient.build()
        dns_api = Dns(client)
        config: dict = self.test_data['TLSA']
        dns_record = dns_api.create_record(
            config['domain'],
            config['record_type'],
            config['content'],
            name=config['name'],
            ttl=config['ttl'],
            prio=config['prio'],
            notes=config['notes']
        )
        self.created_record_ids.append(dns_record.id)
        self.assertTrue(dns_record.id)
        self.assertEqual(config['name'], dns_record.name)
        self.assertEqual(config['record_type'], dns_record.type)

    def test_create_caa_record(self):
        """Test creation of CAA record
        """
        client = PyrkbunClient.build()
        dns_api = Dns(client)
        config: dict = self.test_data['CAA']
        dns_record = dns_api.create_record(
            config['domain'],
            config['record_type'],
            config['content'],
            name=config['name'],
            ttl=config['ttl'],
            prio=config['prio'],
            notes=config['notes']
        )
        self.created_record_ids.append(dns_record.id)
        self.assertTrue(dns_record.id)
        self.assertEqual(config['name'], dns_record.name)
        self.assertEqual(config['record_type'], dns_record.type)

@skipUnless(TEST_DOMAIN_NAME != "", "No test domain configured.")
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
        client = PyrkbunClient.build()
        dns_api = Dns(client)
        for record in test_records:
            create = dns_api.create_record(
                TEST_DOMAIN_NAME,
                record['type'],
                record['content'],
                name=record['name'],
                ttl=record['ttl'],
                prio=record['prio'],
                notes=record['notes']
            )
            test_data = {'id': str(create.id), 'name': record['name'], 'type': record['type']}
            cls.test_records.append(test_data)

    @classmethod
    def tearDownClass(cls) -> None:
        """Cleanup test records if any remain
        """
        client = PyrkbunClient.build()
        dns_api = Dns(client)
        for record in cls.test_records:
            try:
                dns_api.delete_record(TEST_DOMAIN_NAME, record_id=record['id'])
            except ApiError as error:
                if error.message == "Invalid record ID.":
                    pass

    def test_delete_by_id_class_method(self):
        """Test deletion of record by id using class method
        """
        client = PyrkbunClient.build()
        dns_api = Dns(client)
        record = [record for record in self.test_records if record['type'] == 'A'][0]
        # Delete the record (no return value expected, success means no exception)
        dns_api.delete_record(TEST_DOMAIN_NAME, record_id = record['id'])
        # Check that the record is gone
        check = dns_api.get_records(TEST_DOMAIN_NAME, record_id = record['id'])
        self.assertListEqual(check.records, [])

    def test_delete_by_name_type_class_method(self):
        """Test deletion of record by name and type using class method
        """
        client = PyrkbunClient.build()
        dns_api = Dns(client)
        record = [record for record in self.test_records if record['type'] == 'AAAA'][0]
        # Delete the record (no return value expected, success means no exception)
        dns_api.delete_record(TEST_DOMAIN_NAME, record_type=record['type'], name=record['name'])
        # Check that the record is gone
        check = dns_api.get_records(TEST_DOMAIN_NAME, record_id = record['id'])
        self.assertListEqual(check.records, [])

    def test_delete_by_instance_method(self):
        """Test deletion of record using new API
        """
        client = PyrkbunClient.build()
        dns_api = Dns(client)
        record = [record for record in self.test_records if record['type'] == 'MX'][0]
        # In the new API, we delete directly using the DNS API rather than instance methods
        dns_api.delete_record(TEST_DOMAIN_NAME, record_id = record['id'])
        # Check that the record is gone
        check = dns_api.get_records(TEST_DOMAIN_NAME, record_id = record['id'])
        self.assertListEqual(check.records, [])

@skipUnless(TEST_DOMAIN_NAME != "", "No test domain configured.")
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
        client = PyrkbunClient.build()
        dns_api = Dns(client)
        for record in test_records:
            create = dns_api.create_record(
                TEST_DOMAIN_NAME,
                record['type'],
                record['content'],
                name=record['name'],
                ttl=record['ttl'],
                prio=record['prio'],
                notes=record['notes']
            )
            test_data = {'id': str(create.id), 'name': record['name'], 'type': record['type']}
            cls.test_records.append(test_data)

    @classmethod
    def tearDownClass(cls) -> None:
        """Delete test records
        """
        client = PyrkbunClient.build()
        dns_api = Dns(client)
        for record in cls.test_records:
            try:
                dns_api.delete_record(TEST_DOMAIN_NAME, record_id=record['id'])
            except ApiError as error:
                if error.message == "Invalid record ID.":
                    pass

    def test_edit_by_id_class_method(self):
        """Test edit of record by id using class method
        """
        client = PyrkbunClient.build()
        dns_api = Dns(client)
        record = [record for record in self.test_records if record['type'] == 'A'][0]
        # Edit the record and get the updated record object back
        updated_record = dns_api.edit_record(
            TEST_DOMAIN_NAME,
            record_id=record['id'],
            name='pyrkbuntestaedit',
            record_type='A',
            content='198.51.100.55',
            ttl='680',
            prio='0',
            notes='pyrkbun test A record'
        )
        # Verify the update was successful
        self.assertEqual('pyrkbuntestaedit', updated_record.name)
        self.assertEqual('198.51.100.55', updated_record.content)
        self.assertEqual('680', updated_record.ttl)

    def test_edit_by_name_type_class_method(self):
        """Test edit of record by type and name using class method
        """
        client = PyrkbunClient.build()
        dns_api = Dns(client)
        record = [record for record in self.test_records if record['type'] == 'AAAA'][0]
        # Edit the record using name and type (Note: new API requires name and record_type as parameters)
        updated_record = dns_api.edit_record(
            TEST_DOMAIN_NAME,
            record_type=record['type'],
            name=record['name'],
            content='2001:0db8:85a3:0000:0000:8a2e:0370:adef',
            ttl='700',
            prio='0',
            notes='pyrkbun test A record'
        )
        # Verify the update was successful
        self.assertEqual('pyrkbuntestaaaa', updated_record.name)
        self.assertEqual('2001:0db8:85a3:0000:0000:8a2e:0370:adef', updated_record.content)
        self.assertEqual('700', updated_record.ttl)

    def test_edit_by_instance_method(self):
        """Test edit of record using new API (record editing via API calls)
        """
        client = PyrkbunClient.build()
        dns_api = Dns(client)
        record = [record for record in self.test_records if record['type'] == 'CNAME'][0]
        # In the new API, we edit directly through the DNS API rather than instance methods
        updated_record = dns_api.edit_record(
            TEST_DOMAIN_NAME,
            record_id=record['id'],
            name='pyrkbuntestcnameedit',
            record_type=record['type'],
            content=f'pyrkbuntesta.{TEST_DOMAIN_NAME}',
            ttl='770'
        )
        # Verify the update was successful
        self.assertEqual('pyrkbuntestcnameedit', updated_record.name)
        self.assertEqual(f'pyrkbuntesta.{TEST_DOMAIN_NAME}', updated_record.content)
        self.assertEqual('770', updated_record.ttl)

if __name__ == '__main__':
    unittest.main()
