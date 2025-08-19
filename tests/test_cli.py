"""Test Pyrkbun CLI"""
import os
import time
import json
import subprocess
import unittest
from unittest.mock import patch
from os import getenv, path
from httpx import ReadTimeout

try:
    from dotenv import load_dotenv
    load_dotenv()
except ModuleNotFoundError:
    pass

import pyrkbun
from pyrkbun import PyrkbunClient, ApiError, ApiFailure

PYRK_CLI = 'pyrkbun.cli'
TEST_DOMAIN_NAME = getenv("TEST_DOMAIN_NAME","")

class CliIntegrationTestsPing(unittest.TestCase):
    """Test API ping operation from CLI
    """

    def test_ping(self):
        """Test API ping using the v4/v6 API host
        """
        command = ['python', '-m', PYRK_CLI, 'ping']
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        output = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(output['status'], 'SUCCESS')
        self.assertTrue(len(output['yourIp']) >= 7)

    def test_ping_v4_explicit(self):
        """Test API ping using the v4 only API via explicit setting
        """
        command = ['python', '-m', PYRK_CLI, 'ping', '-v4']
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        output = json.loads(result.stdout)
        ip_add = output['yourIp']
        self.assertEqual(result.returncode, 0)
        self.assertEqual(output['status'], 'SUCCESS')
        self.assertEqual(len(ip_add.split('.')), 4)


class PricingCliIntegrationTests(unittest.TestCase):
    """Test pricing API from CLI
    """

    def test_get_pricing(self):
        """Validate data returned from pricing API
        """
        command = ['python', '-m', PYRK_CLI, 'pricing']
        cmd_env = os.environ.copy()
        cmd_env.update({'PYRK_TIMEOUT': '30'})
        result = subprocess.run(command, capture_output=True, text=True, check=True, env=cmd_env )
        output = json.loads(result.stdout)
        price_data: dict = output['pricing']
        self.assertEqual(result.returncode, 0)
        self.assertIn('com', price_data.keys())
        self.assertIn('net', price_data.keys())
        self.assertIn('org', price_data.keys())


class SslCliIntegrationTests(unittest.TestCase):
    """Test SSL API via CLI
    WARNING: This test suite will retirieve private certificate data for your domain
    If the SSL cert is not available for this domian the test will be auto skipped
    """

    def test_get_ssl(self):
        """Validate data returned from SSL API
        """
        command = ['python', '-m', PYRK_CLI, 'ssl', TEST_DOMAIN_NAME]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        if result.stdout == 'Error -> The SSL certificate is not ready for this domain.\n':
            self.skipTest('Skipping test as domain does not hold ssl cert')

        output = json.loads(result.stdout)
        cert_int: str = output["intermediatecertificate"][0:27]
        cert_chain: str = output["certificatechain"][0:27]
        cert_private: str = output["privatekey"][0:27]
        cert_public: str = output["publickey"][0:26]
        self.assertEqual(result.returncode, 0)
        self.assertEqual(cert_int, '-----BEGIN CERTIFICATE-----')
        self.assertEqual(cert_chain, '-----BEGIN CERTIFICATE-----')
        self.assertEqual(cert_private, '-----BEGIN PRIVATE KEY-----')
        self.assertEqual(cert_public, '-----BEGIN PUBLIC KEY-----')


class DnsGetCliIntegrationTests(unittest.TestCase):
    """Test DNS Get, Create, Edit, Delete
    WARNING: This test suite WILL MODIFY your DOMAIN RECORDS
    All records created SHOULD be automatically REMOVED on test completion
    """

    @classmethod
    def setUpClass(cls) -> None:
        """Setup test records
        """
        test_records = [{'name': 'pyrkcligeta',
                         'type': 'A',
                         'content': '198.51.100.45',
                         'ttl': '600',
                         'prio': '0',
                         'notes': 'pyrkbun test A record'},
                        {'name': 'pyrkcligetaaaa',
                         'type': 'AAAA',
                         'content': '2001:0db8:85a3:0000:0000:8a2e:0370:7334',
                         'ttl': '600',
                         'prio': '0',
                         'notes': 'pyrkbun test AAAA record'},
                        {'name': '',
                         'type': 'MX',
                         'content': 'pyrkcligeta.example.com',
                         'ttl': '600',
                         'prio': '65534',
                         'notes': 'pyrkbun test MX record 1'},
                        {'name': '',
                         'type': 'MX',
                         'content': 'pyrkcligetaaaa.example.com',
                         'ttl': '600',
                         'prio': '65533',
                         'notes': 'pyrkbun test MX record 2'}]
        cls.test_records = []
        client = pyrkbun.PyrkbunClient.build()
        dns_api = pyrkbun.dns(client)
        for record in test_records:
            create = dns_api.create_record(TEST_DOMAIN_NAME, record['type'], record['content'],
                                         name=record['name'], ttl=record['ttl'], 
                                         prio=record['prio'], notes=record['notes'])
            test_data = {'id': str(create.id), 'name': record['name'], 'type': record['type']}
            cls.test_records.append(test_data)

    @classmethod
    def tearDownClass(cls) -> None:
        """Cleanup test records
        """
        client = pyrkbun.PyrkbunClient.build()
        dns_api = pyrkbun.dns(client)
        for record in cls.test_records:
            dns_api.delete_record(TEST_DOMAIN_NAME, record_id=record['id'])

    def test_dns_get_all_records(self):
        """Test retrival of all records
        """
        command = ['python', '-m', PYRK_CLI, 'dns', TEST_DOMAIN_NAME, 'get']
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        dns_records = json.loads(result.stdout)
        a_count = 0
        aaaa_count = 0
        mx_count = 0
        for record in dns_records:
            if record['type'] == 'A' and record['name'] == 'pyrkcligeta':
                a_count += 1
            elif record['type'] == 'AAAA' and record['name'] == 'pyrkcligetaaaa':
                aaaa_count += 1
            elif record['type'] == 'MX' and record['content'][0:10] == 'pyrkcliget':
                mx_count += 1
        self.assertEqual(a_count, 1)
        self.assertEqual(aaaa_count, 1)
        self.assertEqual(mx_count, 2)

    def test_get_records_by_type(self):
        """Test retrival of all records by type using cli
        """
        command = ['python', '-m', PYRK_CLI, 'dns', TEST_DOMAIN_NAME, 'get', '-type', 'MX']
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        dns_records = json.loads(result.stdout)
        dns_records = [record for record in dns_records if record['content'][0:10] == 'pyrkcliget'] #pylint: disable=line-too-long
        self.assertEqual(len(dns_records), 2)
        for record in dns_records:
            self.assertIn('id', record.keys())
            self.assertIn('name', record.keys())
            self.assertIn('type', record.keys())
            self.assertIn('content', record.keys())
            self.assertIn('ttl', record.keys())
            self.assertIn('prio', record.keys())
            self.assertEqual('MX', record['type'])

    def test_get_records_by_type_and_name(self):
        """Test retrival by type and name using cli
        """
        command = ['python', '-m', PYRK_CLI, 'dns', TEST_DOMAIN_NAME,
                   'get', '-type', 'A', '-name', 'pyrkcligeta']
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        dns_records = json.loads(result.stdout)
        target_record = dns_records[0]
        self.assertEqual(len(dns_records), 1)
        self.assertEqual('pyrkcligeta', target_record['name'])
        self.assertEqual('A', target_record['type'])

    def test_get_records_by_id(self):
        """Test retrival of records by id using cli
        """
        for test_record in self.test_records:
            command = ['python', '-m', PYRK_CLI, 'dns', TEST_DOMAIN_NAME,
                       'get', '-id', test_record['id']]
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            dns_records = json.loads(result.stdout)
            target_record = dns_records[0]
            self.assertEqual(len(dns_records), 1)
            self.assertEqual(test_record['id'], target_record['id'])
            self.assertEqual(test_record['name'], target_record['name'])
            self.assertEqual(test_record['type'], target_record['type'])

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
        cls.test_data = {'A': {'name': 'pyrkclicreatea',
                               'record_type': 'A',
                               'content': '198.51.100.45',
                               'ttl': '600',
                               'prio': '0',
                               'notes': 'pyrkbun test A record',
                               'domain': TEST_DOMAIN_NAME},
                         'AAAA': {'name': 'pyrkclicreateaaaa',
                                  'record_type': 'AAAA',
                                  'content': '2001:0db8:85a3:0000:0000:8a2e:0370:7334',
                                  'ttl': '600',
                                  'prio': '0',
                                  'notes': 'pyrkbun test AAAA record',
                                  'domain': TEST_DOMAIN_NAME},
                         'MX': {'name': '',
                                'record_type': 'MX',
                                'content': 'pyrkclicreatemx.example.com',
                                'ttl': '600',
                                'prio': '65534',
                                'notes': 'pyrkbun test MX record',
                                'domain': TEST_DOMAIN_NAME},
                         'CNAME': {'name': 'pyrkclicreatecname',
                                   'record_type': 'CNAME',
                                   'content': 'www.example.com',
                                   'ttl': '600',
                                   'prio': '0',
                                   'notes': 'pyrkbun test CNAME record',
                                   'domain': TEST_DOMAIN_NAME},
                         'ALIAS': {'name': 'pyrkclicreatealias',
                                   'record_type': 'ALIAS',
                                   'content': 'www.example.org',
                                   'ttl': '600',
                                   'prio': '0',
                                   'notes': 'pyrkbun test ALIAS record',
                                   'domain': TEST_DOMAIN_NAME},
                         'TXT': {'name': '',
                                 'record_type': 'TXT',
                                 'content': 'txt record cli create test',
                                 'ttl': '600',
                                 'prio': '0',
                                 'notes': 'pyrkbun test TXT record',
                                 'domain': TEST_DOMAIN_NAME},
                         'NS': {'name': f'pyrkclicreatesubdomain.{TEST_DOMAIN_NAME}',
                                'record_type': 'NS',
                                'content': f'pyrkclicreatens.{TEST_DOMAIN_NAME}',
                                'ttl': '600',
                                'prio': '0',
                                'notes': 'pyrkbun test NS record',
                                'domain': TEST_DOMAIN_NAME},
                         'SRV': {'name': '_pyrk._cli',
                                 'record_type': 'SRV',
                                 'content': f'65533 65532 pyrkclicreatesrv.{TEST_DOMAIN_NAME}',
                                 'prio': '65533',
                                 'notes': 'pyrkbun test SRV record',
                                 'domain': TEST_DOMAIN_NAME},
                         'TLSA': {'name': '_443._tcp.pyrkclicreate',
                                  'record_type': 'TLSA',
                                  'content': '0 0 0 123456789abcdef123456789abcdef',
                                  'ttl': '600',
                                  'prio': '0',
                                  'notes': 'pyrkbun test TLSA record',
                                  'domain': TEST_DOMAIN_NAME},
                         'CAA': {'name': '',
                                 'record_type': 'CAA',
                                 'content': f'0 issue "pyrkclicreate.{TEST_DOMAIN_NAME}"',
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
        dns_api = pyrkbun.dns(client)
        for record_id in cls.created_record_ids:
            try:
                dns_api.delete_record(TEST_DOMAIN_NAME, record_id=record_id)
            except (ApiError, ApiFailure, ReadTimeout) as error:
                print(error.message)

    def test_create_a_record(self):
        """Test creation of A record
        """
        config: dict = self.test_data['A']
        command = ['python', '-m', PYRK_CLI, 'dns', TEST_DOMAIN_NAME, 'create',
                   '-name', config['name'], '-type', config['record_type'], '-content',
                   config['content'], '-ttl', config['ttl'], '-priority', config['prio'],
                   '-notes', config['notes']]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        output = json.loads(result.stdout)
        if output['id']:
            self.created_record_ids.append(str(output['id']))
        self.assertTrue(output['id'])
        self.assertIn(str(output['id']), self.created_record_ids)

    def test_create_aaaa_record(self):
        """Test creation of AAAA record
        """
        config: dict = self.test_data['AAAA']
        command = ['python', '-m', PYRK_CLI, 'dns', TEST_DOMAIN_NAME, 'create',
                   '-name', config['name'], '-type', config['record_type'], '-content',
                   config['content'], '-ttl', config['ttl'], '-priority', config['prio'],
                   '-notes', config['notes']]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        output = json.loads(result.stdout)
        if output['id']:
            self.created_record_ids.append(str(output['id']))
        self.assertTrue(output['id'])
        self.assertIn(str(output['id']), self.created_record_ids)

    def test_create_mx_record(self):
        """Test creation of MX record
        """
        config: dict = self.test_data['MX']
        command = ['python', '-m', PYRK_CLI, 'dns', TEST_DOMAIN_NAME, 'create',
                   '-name', config['name'], '-type', config['record_type'], '-content',
                   config['content'], '-ttl', config['ttl'], '-priority', config['prio'],
                   '-notes', config['notes']]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        output = json.loads(result.stdout)
        if output['id']:
            self.created_record_ids.append(str(output['id']))
        self.assertTrue(output['id'])
        self.assertIn(str(output['id']), self.created_record_ids)

    def test_create_cname_record(self):
        """Test creation of CNAME record
        """
        config: dict = self.test_data['CNAME']
        command = ['python', '-m', PYRK_CLI, 'dns', TEST_DOMAIN_NAME, 'create',
                   '-name', config['name'], '-type', config['record_type'], '-content',
                   config['content'], '-ttl', config['ttl'], '-priority', config['prio'],
                   '-notes', config['notes']]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        output = json.loads(result.stdout)
        if output['id']:
            self.created_record_ids.append(str(output['id']))
        self.assertTrue(output['id'])
        self.assertIn(str(output['id']), self.created_record_ids)

    def test_create_alias_record(self):
        """Test creation of ALIAS record
        """
        config: dict = self.test_data['ALIAS']
        command = ['python', '-m', PYRK_CLI, 'dns', TEST_DOMAIN_NAME, 'create',
                   '-name', config['name'], '-type', config['record_type'], '-content',
                   config['content'], '-ttl', config['ttl'], '-priority', config['prio'],
                   '-notes', config['notes']]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        output = json.loads(result.stdout)
        if output['id']:
            self.created_record_ids.append(str(output['id']))
        self.assertTrue(output['id'])
        self.assertIn(str(output['id']), self.created_record_ids)

    def test_create_txt_record(self):
        """Test creation of TXT record
        """
        config: dict = self.test_data['TXT']
        command = ['python', '-m', PYRK_CLI, 'dns', TEST_DOMAIN_NAME, 'create',
                   '-name', config['name'], '-type', config['record_type'], '-content',
                   config['content'], '-ttl', config['ttl'], '-priority', config['prio'],
                   '-notes', config['notes']]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        output = json.loads(result.stdout)
        if output['id']:
            self.created_record_ids.append(str(output['id']))
        self.assertTrue(output['id'])
        self.assertIn(str(output['id']), self.created_record_ids)

    def test_create_ns_record(self):
        """Test creation of NS record
        """
        config: dict = self.test_data['NS']
        command = ['python', '-m', PYRK_CLI, 'dns', TEST_DOMAIN_NAME, 'create',
                   '-name', config['name'], '-type', config['record_type'], '-content',
                   config['content'], '-ttl', config['ttl'], '-priority', config['prio'],
                   '-notes', config['notes']]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        output = json.loads(result.stdout)
        if output['id']:
            self.created_record_ids.append(str(output['id']))
        self.assertTrue(output['id'])
        self.assertIn(str(output['id']), self.created_record_ids)

    def test_create_srv_record(self):
        """Test creation of SRV record
        """
        config: dict = self.test_data['SRV']
        command = ['python', '-m', PYRK_CLI, 'dns', TEST_DOMAIN_NAME, 'create',
                   '-name', config['name'], '-type', config['record_type'], '-content',
                   config['content'], '-priority', config['prio'], '-notes', config['notes']]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        output = json.loads(result.stdout)
        if output['id']:
            self.created_record_ids.append(str(output['id']))
        self.assertTrue(output['id'])
        self.assertIn(str(output['id']), self.created_record_ids)

    def test_create_tlsa_record(self):
        """Test creation of TLSA record
        """
        config: dict = self.test_data['TLSA']
        command = ['python', '-m', PYRK_CLI, 'dns', TEST_DOMAIN_NAME, 'create',
                   '-name', config['name'], '-type', config['record_type'], '-content',
                   config['content'], '-ttl', config['ttl'], '-priority', config['prio'],
                   '-notes', config['notes']]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        output = json.loads(result.stdout)
        if output['id']:
            self.created_record_ids.append(str(output['id']))
        self.assertTrue(output['id'])
        self.assertIn(str(output['id']), self.created_record_ids)

    def test_create_caa_record(self):
        """Test creation of CAA record
        """
        config: dict = self.test_data['CAA']
        command = ['python', '-m', PYRK_CLI, 'dns', TEST_DOMAIN_NAME, 'create',
                   '-name', config['name'], '-type', config['record_type'], '-content',
                   config['content'], '-ttl', config['ttl'], '-priority', config['prio'],
                   '-notes', config['notes']]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        output = json.loads(result.stdout)
        if output['id']:
            self.created_record_ids.append(str(output['id']))
        self.assertTrue(output['id'])
        self.assertIn(str(output['id']), self.created_record_ids)

class DnsDeleteIntegrationTests(unittest.TestCase):
    """Test DNS API for record deletion
    WARNING: This test suite WILL MODIFY your DOMAIN RECORDS
    All records created SHOULD be automatically REMOVED on test completion
    """

    @classmethod
    def setUpClass(cls) -> None:
        """Setup test records
        """
        test_records = [{'name': 'pyrkclidela',
                         'type': 'A',
                         'content': '198.51.100.45',
                         'ttl': '600',
                         'prio': '0',
                         'notes': 'pyrkbun test A record'},
                        {'name': 'pyrkclidelaaaa',
                         'type': 'AAAA',
                         'content': '2001:0db8:85a3:0000:0000:8a2e:0370:7334',
                         'ttl': '600',
                         'prio': '0',
                         'notes': 'pyrkbun test AAAA record'}]
        cls.test_records = []
        client = pyrkbun.PyrkbunClient.build()
        dns_api = pyrkbun.dns(client)
        for record in test_records:
            create = dns_api.create_record(TEST_DOMAIN_NAME, record['type'], record['content'],
                                         name=record['name'], ttl=record['ttl'], 
                                         prio=record['prio'], notes=record['notes'])
            test_data = {'id': str(create.id), 'name': record['name'], 'type': record['type']}
            cls.test_records.append(test_data)

    @classmethod
    def tearDownClass(cls) -> None:
        """Cleanup test records if any remain
        """
        client = pyrkbun.PyrkbunClient.build()
        dns_api = pyrkbun.dns(client)
        for record in cls.test_records:
            try:
                dns_api.delete_record(TEST_DOMAIN_NAME, record_id=record['id'])
            except ApiError as error:
                if error.message == "Invalid record ID.":
                    pass

    def test_delete_by_id(self):
        """Test deletion of record by id
        """
        record = [record for record in self.test_records if record['type'] == 'A'][0]
        command = ['python', '-m', PYRK_CLI, 'dns', TEST_DOMAIN_NAME, 'delete',
                   '-id', record['id']]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        output = json.loads(result.stdout)
        client = pyrkbun.PyrkbunClient.build()
        dns_api = pyrkbun.dns(client)
        check = dns_api.get_records(TEST_DOMAIN_NAME, record_id=record['id'])
        self.assertEqual('SUCCESS', output['status'])
        self.assertListEqual(check.records, [])

    def test_delete_by_name_type(self):
        """Test deletion of record by name and type
        """
        record = [record for record in self.test_records if record['type'] == 'AAAA'][0]
        command = ['python', '-m', PYRK_CLI, 'dns', TEST_DOMAIN_NAME, 'delete',
                   '-name', record['name'], '-type', record['type']]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        output = json.loads(result.stdout)
        client = pyrkbun.PyrkbunClient.build()
        dns_api = pyrkbun.dns(client)
        check = dns_api.get_records(TEST_DOMAIN_NAME, record_id=record['id'])
        self.assertListEqual(check.records, [])

class DnsModifyIntegrationTests(unittest.TestCase):
    """Test DNS API for record modification
    WARNING: This test suite WILL MODIFY your DOMAIN RECORDS
    All records created SHOULD be automatically REMOVED on test completion
    """

    @classmethod
    def setUpClass(cls) -> None:
        """Create test records
        """
        test_records = [{'name': 'pyrkcliedita',
                         'type': 'A',
                         'content': '198.51.100.45',
                         'ttl': '600',
                         'prio': '0',
                         'notes': 'pyrkbun test A record'},
                        {'name': 'pyrkclieditaaaa',
                         'type': 'AAAA',
                         'content': '2001:0db8:85a3:0000:0000:8a2e:0370:7334',
                         'ttl': '600',
                         'prio': '0',
                         'notes': 'pyrkbun test AAAA record'}]
        cls.test_records = []
        client = pyrkbun.PyrkbunClient.build()
        dns_api = pyrkbun.dns(client)
        for record in test_records:
            create = dns_api.create_record(TEST_DOMAIN_NAME, record['type'], record['content'],
                                         name=record['name'], ttl=record['ttl'], 
                                         prio=record['prio'], notes=record['notes'])
            test_data = {'id': str(create.id), 'name': record['name'], 'type': record['type']}
            cls.test_records.append(test_data)

    @classmethod
    def tearDownClass(cls) -> None:
        """Delete test records
        """
        client = pyrkbun.PyrkbunClient.build()
        dns_api = pyrkbun.dns(client)
        for record in cls.test_records:
            try:
                dns_api.delete_record(TEST_DOMAIN_NAME, record_id=record['id'])
            except ApiError as error:
                if error.message == "Invalid record ID.":
                    pass

    def test_edit_by_id(self):
        """Test edit of record by id
        """
        record = [record for record in self.test_records if record['type'] == 'A'][0]
        command = ['python', '-m', PYRK_CLI, 'dns', TEST_DOMAIN_NAME, 'edit',
                   '-id', record['id'], '-name', 'pyrkclieditaedit', '-ttl', '680',
                   '-content', '198.51.100.55', '-type', 'A']
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        output = json.loads(result.stdout)
        client = pyrkbun.PyrkbunClient.build()
        dns_api = pyrkbun.dns(client)
        check = dns_api.get_records(TEST_DOMAIN_NAME, record_id=record['id']).records[0]
        self.assertEqual('pyrkclieditaedit', check.name)
        self.assertEqual('198.51.100.55', check.content)
        self.assertEqual('680', check.ttl)

    def test_edit_by_name_type(self):
        """Test edit of record by type and name
        """
        record = [record for record in self.test_records if record['type'] == 'AAAA'][0]
        command = ['python', '-m', PYRK_CLI, 'dns', TEST_DOMAIN_NAME, 'edit',
                   '-id', record['id'], '-name', 'pyrkclieditaaaa', '-ttl', '700',
                   '-content', '2001:0db8:85a3:0000:0000:8a2e:0370:adef', '-type', 'AAAA']
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        output = json.loads(result.stdout)
        client = pyrkbun.PyrkbunClient.build()
        dns_api = pyrkbun.dns(client)
        check = dns_api.get_records(TEST_DOMAIN_NAME, record_id=record['id']).records[0]
        self.assertEqual('pyrkclieditaaaa', check.name)
        self.assertEqual('2001:0db8:85a3:0000:0000:8a2e:0370:adef', check.content)
        self.assertEqual('700', check.ttl)


class DnsBulkCliIntegrationTests(unittest.TestCase):
    """Test DNS Get, Create, Edit, Delete
    WARNING: This test suite WILL MODIFY your DOMAIN RECORDS
    All records created SHOULD be automatically REMOVED on test completion
    One of these tests will WIPE your EXISTING DOMAIN records.
    A backup will be taken before running but cannot garuntee
    it will successfully restore (it's a test)
    """

    @classmethod
    def setUpClass(cls) -> None:
        """Backup existing domain records
        """
        client = pyrkbun.PyrkbunClient.build()
        dns_api = pyrkbun.dns(client)
        backup = dns_api.get_records(TEST_DOMAIN_NAME)
        cls.backup = [record for record in backup.records if record.type != 'NS']

    @classmethod
    def tearDownClass(cls) -> None:
        """Clean up any records left after test run and restore backup
        """
        client = pyrkbun.PyrkbunClient.build()
        dns_api = pyrkbun.dns(client)
        cleanup = dns_api.get_records(TEST_DOMAIN_NAME)
        cleanup = [record for record in cleanup.records if record.type != 'NS']
        for record in cleanup:
            dns_api.delete_record(TEST_DOMAIN_NAME, record_id=record.id)
        for record in cls.backup:
            dns_api.create_record(TEST_DOMAIN_NAME, record.type, record.content,
                                name=record.name, ttl=record.ttl, 
                                prio=record.prio, notes=record.notes)

    def setUp(self) -> None:
        """Setup test records
        """
        test_records = [{'name': 'pyrkclibulka',
                         'type': 'A',
                         'content': '198.51.100.45',
                         'ttl': '600',
                         'prio': '0',
                         'notes': 'pyrkbun test A record'},
                        {'name': 'pyrkclibulkaaaa',
                         'type': 'AAAA',
                         'content': '2001:0db8:85a3:0000:0000:8a2e:0370:7334',
                         'ttl': '600',
                         'prio': '0',
                         'notes': 'pyrkbun test AAAA record'},
                        {'name': '',
                         'type': 'MX',
                         'content': 'pyrkclibulkaaaa.example.com',
                         'ttl': '600',
                         'prio': '65533',
                         'notes': 'pyrkbun test MX record 1'}]
        self.test_records = []
        client = pyrkbun.PyrkbunClient.build()
        dns_api = pyrkbun.dns(client)
        for record in test_records:
            create = dns_api.create_record(TEST_DOMAIN_NAME, record['type'], record['content'],
                                         name=record['name'], ttl=record['ttl'], 
                                         prio=record['prio'], notes=record['notes'])
            test_data = {'id': str(create.id), 'name': record['name'], 'type': record['type']}
            self.test_records.append(test_data)
        time.sleep(10)

    def tearDown(self) -> None:
        """Cleanup test records
        """
        client = pyrkbun.PyrkbunClient.build()
        dns_api = pyrkbun.dns(client)
        cleanup = dns_api.get_records(TEST_DOMAIN_NAME)
        cleanup = [record for record in cleanup.records if record.type != 'NS']
        for record in cleanup:
            try:
                dns_api.delete_record(TEST_DOMAIN_NAME, record_id=record.id)
            except ApiError as error:
                if error.message == "Invalid record ID.":
                    pass
        time.sleep(10)

    def test_dns_bulk_flush(self):
        """Test bulk operation using 'flush' mode
        """
        command = ['python', '-m', PYRK_CLI, 'dns', TEST_DOMAIN_NAME, 'bulk',
                   './tests/fixtures/bulk_test_flush_input.json',
                   './tests/fixtures/bulk_test_flush_output.json',
                   '-mode', 'flush']
        subprocess.run(command, capture_output=True, text=True, check=True)
        client = pyrkbun.PyrkbunClient.build()
        dns_api = pyrkbun.dns(client)
        check = dns_api.get_records(TEST_DOMAIN_NAME)
        check = [record for record in check.records if record.type != 'NS']
        with open('./tests/fixtures/bulk_test_flush_output.json', 'r', encoding='utf8') as file:
            output = json.load(file)
        self.assertTrue(path.exists('./tests/fixtures/bulk_test_flush_output.json'))
        self.assertEqual(len(output['CREATED']['SUCCESS']), 2)
        self.assertEqual(len(check), 2)
        self.assertEqual(len(output['DELETED']['SUCCESS']), 3)
        for record in check:
            self.assertIn(record.content, ('198.51.100.55', 'pyrkclibulkaflush.example.com'))
            self.assertIn(record.type, ('A', 'MX'))
            self.assertIsNotNone(record.id)

    def test_dns_bulk_add(self):
        """Test bulk operation using 'add' mode
        """
        command = ['python', '-m', PYRK_CLI, 'dns', TEST_DOMAIN_NAME, 'bulk',
                   './tests/fixtures/bulk_test_add_input.json',
                   './tests/fixtures/bulk_test_add_output.json',
                   '-mode', 'add']
        subprocess.run(command, capture_output=True, text=True, check=True)
        client = pyrkbun.PyrkbunClient.build()
        dns_api = pyrkbun.dns(client)
        check = dns_api.get_records(TEST_DOMAIN_NAME)
        check = [record for record in check.records if record.type != 'NS']
        with open('./tests/fixtures/bulk_test_add_output.json', 'r', encoding='utf8') as file:
            results = json.load(file)
        output = []
        for item in results['CREATED']['SUCCESS']:
            for key, value in item.items():
                if key == 'record':
                    output.append(value)
        self.assertTrue(path.exists('./tests/fixtures/bulk_test_add_output.json'))
        self.assertEqual(len(output), 2)
        self.assertEqual(len(check), 5)
        for record in output:
            self.assertIn(record['content'], ('198.51.100.55', 'pyrkclibulkaadd.example.com'))
            self.assertIn(record['type'], ('A', 'MX'))
            self.assertIn('id', record.keys())

    def test_dns_bulk_merge(self):
        """Test bulk operation using 'merge' mode
        """
        pre_input_file = './tests/fixtures/bulk_test_merge_preinput.json'
        input_file = './tests/fixtures/bulk_test_merge_input.json'
        # This section is to ensure the record ID is available for the
        # Records to be edited by loading in the ID collected in the
        # setUp method
        with open(pre_input_file, 'r', encoding='utf8') as file:
            edit_content = json.load(file)
        edit_record_ids = []
        for edit_record in edit_content:
            for test_record in self.test_records:
                if edit_record['name'] == test_record['name']:
                    edit_record.update({'id': test_record['id']})
                    edit_record_ids.append(test_record['id'])

        with open(input_file, 'w', encoding='utf8') as file:
            json.dump(edit_content, file)

        command = ['python', '-m', PYRK_CLI, 'dns', TEST_DOMAIN_NAME, 'bulk',
                   './tests/fixtures/bulk_test_merge_input.json',
                   './tests/fixtures/bulk_test_merge_output.json',
                   '-mode', 'merge']
        subprocess.run(command, capture_output=True, text=True, check=True)
        client = pyrkbun.PyrkbunClient.build()
        dns_api = pyrkbun.dns(client)
        check = dns_api.get_records(TEST_DOMAIN_NAME)
        check = [record for record in check.records if record.type != 'NS']
        with open('./tests/fixtures/bulk_test_merge_output.json', 'r', encoding='utf8') as file:
            results = json.load(file)
        created = []
        for item in results['CREATED']['SUCCESS']:
            for key, value in item.items():
                if key == 'record':
                    created.append(value)

        for record in check:
            if record.id in edit_record_ids:
                self.assertIn(record.content,
                              ('198.51.100.101', '2001:0db8:85a3:0000:0000:8a2e:0370:abcd'))
                self.assertIn(record.type, ('A', 'AAAA'))
                self.assertIn(record.name, ('pyrkclibulka', 'pyrkclibulkaaaa'))

            elif record.id == created[0]['id']:
                self.assertEqual(record.name, 'pyrkclibulkamerge')
        self.assertTrue(path.exists('./tests/fixtures/bulk_test_merge_output.json'))
        self.assertEqual(len(created), 1)


if __name__ == 'main':
    unittest.main()
