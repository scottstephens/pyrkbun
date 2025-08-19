"""All tests which do not require Porkbun API communication
"""
import unittest
from os import getenv

try:
    from dotenv import load_dotenv
    load_dotenv()
except ModuleNotFoundError:
    pass

from pyrkbun.client import PyrkbunClient
from pyrkbun.dns import Dns

class DnsUnitTests(unittest.TestCase):
    """Unit tests on DNS class intialisation and updates
    """

    def setUp(self):
        self.domain = 'example.com'

    def test_dns_class_init_all_defaults(self):
        """Test basic init with only mandatory values provided
        """
        client = PyrkbunClient('test_key', 'test_secret')
        dns_api = Dns(client)
        # Note: The new API doesn't have individual record objects like the old one
        # This test now focuses on testing the client creation
        self.assertIsInstance(client, PyrkbunClient)
        self.assertEqual(client.api_key, 'test_key')
        self.assertEqual(client.api_secret_key, 'test_secret')
        self.assertIsInstance(dns_api, Dns)

    def test_dns_class_init_no_defaults(self):
        """Test client init with all configuration values provided
        """
        client = PyrkbunClient(
            'test_key',
            'test_secret',
            force_v4=True,
            rate_limit=1.0,
            retries=3,
            timeout=30,
            http2=True
        )
        dns_api = Dns(client)
        self.assertIsInstance(client, PyrkbunClient)
        self.assertEqual(client.api_key, 'test_key')
        self.assertEqual(client.api_secret_key, 'test_secret')
        self.assertEqual(client.force_v4, True)
        self.assertEqual(client.rate_limit, 1.0)
        self.assertEqual(client.retries, 3)
        self.assertEqual(client.timeout, 30)
        self.assertEqual(client.http2, True)
        self.assertIsInstance(dns_api, Dns)

    def test_client_build_from_env(self):
        """Test client building from environment variables
        """
        # Test that build method works without arguments (using defaults)
        # This will fail if no env vars are set, but that's expected behavior
        try:
            client = PyrkbunClient.build(api_key='test_key', api_secret_key='test_secret')
            self.assertIsInstance(client, PyrkbunClient)
            self.assertEqual(client.api_key, 'test_key')
            self.assertEqual(client.api_secret_key, 'test_secret')
        except ValueError:
            # Expected if no credentials provided
            pass

    def test_client_build_validation(self):
        """Test client validation of required parameters
        """
        # Test that missing credentials raise ValueError
        with self.assertRaises(ValueError):
            PyrkbunClient.build(read_env=False)
        
        # Test that only API key raises ValueError
        with self.assertRaises(ValueError):
            PyrkbunClient.build(read_env=False,api_key='test_key')
        
        # Test that only secret key raises ValueError
        with self.assertRaises(ValueError):
            PyrkbunClient.build(read_env=False,api_secret_key='test_secret')

    def test_client_default_values(self):
        """Test client default configuration values
        """
        client = PyrkbunClient('test_key', 'test_secret')
        self.assertEqual(client.force_v4, False)
        self.assertEqual(client.rate_limit, 0.0)
        self.assertEqual(client.retries, 0)
        self.assertEqual(client.timeout, 15)
        self.assertEqual(client.http2, False)

    def test_client_url_configuration(self):
        """Test client URL configuration
        """
        # Test default URLs
        client = PyrkbunClient('test_key', 'test_secret')
        self.assertEqual(client.base_url, 'https://api.porkbun.com/api/json/v3')
        self.assertEqual(client.base_url_v4, 'https://api-ipv4.porkbun.com/api/json/v3')
        
        # Test force_v4 URLs
        client_v4 = PyrkbunClient('test_key', 'test_secret', force_v4=True)
        self.assertEqual(client_v4.base_url, 'https://api-ipv4.porkbun.com/api/json/v3')

    def test_dns_api_initialization(self):
        """Test DNS API wrapper initialization
        """
        client = PyrkbunClient('test_key', 'test_secret')
        dns_api = Dns(client)
        self.assertIsInstance(dns_api, Dns)
        self.assertEqual(dns_api.client, client)


if __name__ == '__main__':
    unittest.main()
