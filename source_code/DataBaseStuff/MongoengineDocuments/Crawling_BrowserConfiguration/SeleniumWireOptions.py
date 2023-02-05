from mongoengine import EmbeddedDocument, BooleanField, ListField, DictField, StringField, IntField


class SeleniumWireOptions(EmbeddedDocument):
    """
        Seleniumwire options:
            'disable_capture': True  # Don't intercept/store any requests
            'exclude_hosts': ['host1.com', 'host2.com']  # Bypass Selenium Wire for these hosts
            'request_storage_base_dir': '/my/storage/folder'  # .SeleniumWire will get created here
            'request_storage': 'memory'  # Store requests and responses in memory only
            request_storage_max_size': 100  # Store no more than 100 requests in memory
            'proxy': {'https': 'https://user:pass@192.168.10.100:8888',}
            'proxy': {'https': 'https://192.168.10.100:8888',  # No username or password used 'custom_authorization': 'Bearer mytoken123'  # Custom Proxy-Authorization header value }
            running selenium wire with Tor is possible
    """
    disable_capture = BooleanField(default=False)
    exclude_hosts = ListField(default=['127.0.0.1'])
    proxy = DictField(default={})
    request_storage_base_dir = StringField()
    request_storage_memory = BooleanField(default=True)
    port = IntField(default=30004)
