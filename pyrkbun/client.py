"""Porkbun API client
"""
import json
import time
from os import getenv
from pathlib import Path
from typing import Optional, Dict, Any
import httpx

from .const import VALID_HTTP_RESPONSE

try:
    from dotenv import load_dotenv # type: ignore
    load_dotenv()
except ModuleNotFoundError:
    pass


class ApiError(Exception):
    """Porkbun REST API Error

    Attributes:
        http_status: HTTP status code returned from API
        status: Status message returned from API. Should always be 'Error'
        message: Error message returned from API explains the error cause.
    """

    def __init__(self, http_status, status, message):
        super().__init__(message)
        self.http_status: int = http_status
        self.status: str = status
        self.message: str = message

    def __repr__(self) -> str:
        return f'ApiError({self.http_status}, {self.status}, {self.message})'


class ApiFailure(Exception):
    """Porkbun REST API Failure - non-json return

    Attributes:
        http_status: HTTP status code returned from API
        message: Content returned from server
    """

    def __init__(self, http_status, message):
        super().__init__(message)
        self.http_status: int = http_status
        self.message: str = message

    def __repr__(self) -> str:
        return f'ApiError({self.http_status}, {self.message})'


class PyrkbunClient:
    """Porkbun API client with configuration management
    
    Attributes:
        api_key: Porkbun API Key
        api_secret_key: Porkbun API Secret Key  
        base_url: API base URL to use for requests
        rate_limit: Rate limiting delay between requests (seconds)
        retries: Number of HTTP retries for failed requests
        timeout: HTTP request timeout (seconds)
        http2: Whether to use HTTP/2 (1 for enabled, 0 for disabled)
    """
    
    def __init__(self, 
                 api_key: str,
                 api_secret_key: str,
                 force_v4: bool = False,
                 rate_limit: float = 0.0,
                 retries: int = 0,
                 timeout: int = 15,
                 http2: bool = False):
        """Initialize PyrkbunClient with configuration.

        See also build for a method that can read from config files
        and environment variables.
        
        Args:
            api_key: API key (required)
            api_secret_key: API secret key (required)
            force_v4: Force IPv4 API endpoint (default: False)
            rate_limit: Rate limit delay in seconds (default: 0.0)
            retries: HTTP retries (default: 0)
            timeout: Request timeout in seconds (default: 15)
            http2: HTTP/2 enabled (default: False)
        """
        self.api_key = api_key
        self.api_secret_key = api_secret_key
        self.force_v4 = force_v4
        self.rate_limit = rate_limit
        self.retries = retries
        self.timeout = timeout
        self.http2 = http2
        
        # Set base URLs
        self.base_url_v64 = 'https://api.porkbun.com/api/json/v3'
        self.base_url_v4 = 'https://api-ipv4.porkbun.com/api/json/v3'
        self.base_url = self.base_url_v4 if self.force_v4 else self.base_url_v64

    @classmethod
    def build(cls,
              api_key: Optional[str] = None,
              api_secret_key: Optional[str] = None,
              force_v4: Optional[bool] = None,
              rate_limit: Optional[float] = None,
              retries: Optional[int] = None,
              timeout: Optional[int] = None,
              http2: Optional[bool] = None,
              file_name: Optional[str] = None,
              read_env: bool = True) -> 'PyrkbunClient':
        """Build a PyrkbunClient with hierarchical configuration loading
        
        Configuration priority (highest to lowest):
        1. Values specified as arguments to build()
        2. Values from file specified by file_name parameter
        3. Values from individual environment variables (if read_env=True)
        4. Values from config file specified by PYRK_CONFIG_FILE env var
        5. Default values
        
        Args:
            api_key: API key override
            api_secret_key: API secret key override
            force_v4: Force IPv4 endpoint override
            rate_limit: Rate limit override
            retries: HTTP retries override
            timeout: Request timeout override
            http2: HTTP/2 setting override
            file_name: Path to JSON config file
            read_env: Whether to read from environment variables
            
        Returns:
            Configured PyrkbunClient instance
        """
        # Load configuration in priority order (lowest to highest)
        config = cls._get_default_config()
        if read_env:
            config.update(cls._load_config_from_env_file())
            config.update(cls._load_config_from_env_vars())
        if file_name:
            config.update(cls._load_config_file(file_name))
        config.update(cls._load_config_from_args(
            api_key, api_secret_key, force_v4, rate_limit, retries, timeout, http2
        ))
        
        # Validate required fields
        if not config['api_key'] or not config['api_secret_key']:
            raise ValueError("api_key and api_secret_key are required")
        
        return cls(
            api_key=config['api_key'],
            api_secret_key=config['api_secret_key'],
            force_v4=config['force_v4'],
            rate_limit=config['rate_limit'],
            retries=config['retries'],
            timeout=config['timeout'],
            http2=config['http2']
        )

    @staticmethod
    def _get_default_config() -> Dict[str, Any]:
        """Get default configuration values"""
        return {
            'api_key': None,
            'api_secret_key': None,
            'force_v4': False,
            'rate_limit': 0.0,
            'retries': 0,
            'timeout': 15,
            'http2': False
        }

    @staticmethod
    def _load_config_from_env_file() -> Dict[str, Any]:
        """Load configuration from PYRK_CONFIG_FILE environment variable"""
        config_file_path = getenv('PYRK_CONFIG_FILE')
        if config_file_path:
            return PyrkbunClient._load_config_file(config_file_path)
        return {}

    @staticmethod
    def _load_config_from_env_vars() -> Dict[str, Any]:
        """Load configuration from individual environment variables"""
        config = {}
        PyrkbunClient._add_env_var(config, 'PYRK_API_KEY', 'api_key', str)
        PyrkbunClient._add_env_var(config, 'PYRK_API_SECRET_KEY', 'api_secret_key', str)
        PyrkbunClient._add_env_var(config, 'PYRK_FORCE_V4', 'force_v4', lambda x: bool(x))
        PyrkbunClient._add_env_var(config, 'PYRK_RATE', 'rate_limit', float)
        PyrkbunClient._add_env_var(config, 'PYRK_RETRIES', 'retries', int)
        PyrkbunClient._add_env_var(config, 'PYRK_TIMEOUT', 'timeout', int)
        PyrkbunClient._add_env_var(config, 'PYRK_HTTP2', 'http2', lambda x: bool(int(x)))
        return config

    @staticmethod
    def _add_env_var(config: Dict[str, Any], env_name: str, config_key: str, converter) -> None:
        """Add an environment variable to config dict if it exists"""
        value = getenv(env_name)
        if value:
            config[config_key] = converter(value)

    @staticmethod
    def _load_config_from_args(api_key: Optional[str],
                               api_secret_key: Optional[str],
                               force_v4: Optional[bool],
                               rate_limit: Optional[float],
                               retries: Optional[int],
                               timeout: Optional[int],
                               http2: Optional[bool]) -> Dict[str, Any]:
        """Load configuration from method arguments"""
        config = {}
        if api_key is not None:
            config['api_key'] = api_key
        if api_secret_key is not None:
            config['api_secret_key'] = api_secret_key
        if force_v4 is not None:
            config['force_v4'] = force_v4
        if rate_limit is not None:
            config['rate_limit'] = rate_limit
        if retries is not None:
            config['retries'] = retries
        if timeout is not None:
            config['timeout'] = timeout
        if http2 is not None:
            config['http2'] = http2
        return config

    @staticmethod
    def _load_config_file(file_path: str) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            path = Path(file_path)
            if not path.exists():
                return {}
            
            with open(path, 'r') as f:
                file_config = json.load(f)
            
            # Map JSON keys to expected config keys if needed
            config = {}
            key_mapping = {
                'api_key': 'api_key',
                'api_secret_key': 'api_secret_key', 
                'force_v4': 'force_v4',
                'rate_limit': 'rate_limit',
                'retries': 'retries',
                'timeout': 'timeout',
                'http2': 'http2'
            }
            
            for json_key, config_key in key_mapping.items():
                if json_key in file_config:
                    value = file_config[json_key]
                    # Handle http2 conversion from int to bool if needed
                    if config_key == 'http2' and isinstance(value, int):
                        value = bool(value)
                    config[config_key] = value
            
            return config
        except (json.JSONDecodeError, IOError):
            return {}

    def api_post(self, path: str,
                 payload: dict | None = None,
                 auth: bool = True,
                 force_v4: bool = False,
                 retries: int | None = None) -> dict:
        """Format request and post to API endpoint

        Args:
            path: Section of API path that extends base URL
                (e.g. /dns/create/<domain>).
            payload (optional): JSON payload for API request formatted as dict.
                Payload will automatically be updated with API keys.
                Defaults to empty dict
            auth (optional): Does the API request require authentication.
                Defaults to True which auto updates payload with auth data
            force_v4 (optional): Force IPv4 endpoint for this request
            retries (optional): Override default retries for this request

        Raises:
            ApiError(): If the API returns a non-200 status code an error will be
                raised encapsulating the error message and http status-code
            ApiFailure(): If JSON decoding of the returned data fails this error
                will be raised encapsulating the content returned
        """
        payload = {} if payload is None else payload
        base_url = self.base_url_v4 if force_v4 else self.base_url
        retries = retries if retries is not None else self.retries
        
        if auth:
            payload.update({'secretapikey': self.api_secret_key, 'apikey': self.api_key})
            
        transport = httpx.HTTPTransport(retries=retries)
        headers = {'content-type': 'application/json'}
        http_client = httpx.Client(
            http2=self.http2, 
            base_url=base_url, 
            headers=headers, 
            transport=transport, 
            timeout=self.timeout
        )
        
        with http_client as client:
            time.sleep(self.rate_limit)
            response = client.post(path, json=payload)

        try:
            result: dict = response.json()
        except ValueError as error:
            print(response.status_code)
            print(response.content)
            raise ApiFailure(response.status_code, response.content) from error

        # Remove api auth data added to keys to prevent accidental exposure and allow
        # reuse of dicts provided to create and update functions
        payload.pop('apikey', None)
        payload.pop('secretapikey', None)

        if response.status_code in VALID_HTTP_RESPONSE:
            return result
        else:
            result.update({'http_status': response.status_code})
            raise ApiError(**result)

    def ping(self, ipv4: bool = False) -> dict:
        """Basic request to poll API host and return your own IP

        Args:
            ipv4: Force IPv4 endpoint for ping request

        Example:
            >>> client = PyrkbunClient()
            >>> response = client.ping()
            >>> print(response)
            {'status': 'SUCCESS', 'yourIp': '2001:0db8:85a3:0000:0000:8a2e:0370:7334'}
        """
        path = '/ping'
        response = self.api_post(path, force_v4=ipv4)
        return response