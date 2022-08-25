"""All tests which do not require Porkbun API communication
"""
import unittest

import pyrkbun


class DnsUnitTests(unittest.TestCase):
    """Unit tests on DNS class intialisation and updates
    """

    def setUp(self):
        self.domain = 'example.com'

    def test_dns_class_init_all_defaults(self):
        """Test basic init with only mandatory values provided
        """
        dns_record = pyrkbun.dns('example.com', 'A', '198.51.100.45', 'www')
        self.assertIsInstance(dns_record, pyrkbun.dns)
        self.assertEqual(dns_record.domain, 'example.com')
        self.assertEqual(dns_record.name, 'www')
        self.assertEqual(dns_record.record_type, 'A')
        self.assertEqual(dns_record.content, '198.51.100.45')
        self.assertEqual(dns_record.ttl, '600')
        self.assertEqual(dns_record.prio, '0')
        self.assertEqual(dns_record.notes, '')

    def test_dns_class_init_no_defaults(self):
        """Test basic init with all values provided
        """
        dns_record = pyrkbun.dns('example.com',
                                 'MX',
                                 'mail.example.com',
                                 '',
                                 '660',
                                 '10',
                                 'This is a test note')
        self.assertIsInstance(dns_record, pyrkbun.dns)
        self.assertEqual(dns_record.domain, 'example.com')
        self.assertEqual(dns_record.name, '')
        self.assertEqual(dns_record.record_type, 'MX')
        self.assertEqual(dns_record.content, 'mail.example.com')
        self.assertEqual(dns_record.ttl, '660')
        self.assertEqual(dns_record.prio, '10')
        self.assertEqual(dns_record.notes, 'This is a test note')

    def test_dns_class_init_with_fqdn_as_name(self):
        """Test domain stripping from record name - fqdn provided as name
        """
        dns_record = pyrkbun.dns('example.com',
                                 'CNAME',
                                 'www.example.com',
                                 'web.example.com',
                                 '660',
                                 '0',
                                 'This is a test note')
        self.assertIsInstance(dns_record, pyrkbun.dns)
        self.assertEqual(dns_record.domain, 'example.com')
        self.assertEqual(dns_record.name, 'web')
        self.assertEqual(dns_record.record_type, 'CNAME')
        self.assertEqual(dns_record.content, 'www.example.com')
        self.assertEqual(dns_record.ttl, '660')
        self.assertEqual(dns_record.prio, '0')
        self.assertEqual(dns_record.notes, 'This is a test note')

    def test_dns_class_init_with_domain_as_name(self):
        """Test domain stripping from record name - domain provided as name
        """
        dns_record = pyrkbun.dns('example.com',
                                 'TXT',
                                 'v=spf1 -all',
                                 'example.com',
                                 '660',
                                 '0',
                                 'Disable email sending')
        self.assertIsInstance(dns_record, pyrkbun.dns)
        self.assertEqual(dns_record.domain, 'example.com')
        self.assertEqual(dns_record.name, '')
        self.assertEqual(dns_record.record_type, 'TXT')
        self.assertEqual(dns_record.content, 'v=spf1 -all')
        self.assertEqual(dns_record.ttl, '660')
        self.assertEqual(dns_record.prio, '0')
        self.assertEqual(dns_record.notes, 'Disable email sending')

    def test_dns_class_init_with_bad_record_type(self):
        """Test record type checking on init
        """
        with self.assertRaises(AssertionError):
            # pylint: disable=unused-variable
            dns_record = pyrkbun.dns('example.com', 'FOO', 'www.example.com')

    def test_dns_class_record_updates(self):
        """Test changes to record post init
        """
        dns_record = pyrkbun.dns('example.com', 'A', '198.51.100.45', 'www')
        dns_record.name = 'www2.example.com'
        dns_record.record_type = 'CNAME'
        dns_record.content = 'www.example.com'
        dns_record.ttl = '680'
        self.assertIsInstance(dns_record, pyrkbun.dns)
        self.assertEqual(dns_record.domain, 'example.com')
        self.assertEqual(dns_record.name, 'www2')
        self.assertEqual(dns_record.record_type, 'CNAME')
        self.assertEqual(dns_record.content, 'www.example.com')
        self.assertEqual(dns_record.ttl, '680')
        self.assertEqual(dns_record.prio, '0')
        self.assertEqual(dns_record.notes, '')

    def test_dns_class_record_update_with_bad_record_type(self):
        """Test record type checking on change post init
        """
        dns_record = pyrkbun.dns('example.com', 'A', 'www.example.com')
        with self.assertRaises(AssertionError):
            dns_record.record_type = 'BAR'


if __name__ == '__main__':
    unittest.main()
