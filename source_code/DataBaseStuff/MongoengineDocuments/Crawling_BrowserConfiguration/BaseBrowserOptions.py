from mongoengine import EmbeddedDocument, BooleanField, IntField, FloatField, EmbeddedDocumentField, StringField, \
    ListField, DictField


class BaseBrowserOptions(EmbeddedDocument):
    meta = {'allow_inheritance': True}

    browser_privacy_level = StringField(default='max_data', choices=['max_data', 'privacy'])
    browser_safebrowsing = BooleanField(default=False)

    use_tor = BooleanField(default=False)

    command_line_switches = ListField(default=list)
    preferences = DictField(default=dict) #[[name, value]]

    def get_webdriver_options_object(self, download_dir='', start_profile_path=''):
        raise NotImplementedError


class ChromiumBasedOptions(BaseBrowserOptions):
    meta = {'allow_inheritance': True}

    class GeoLocation(EmbeddedDocument):
        latitude = FloatField(default=50.1109, required=True)
        longitude = FloatField(default=8.6821, required=True)
        accuracy = IntField(default=100, required=True)

        def __dict__(self):
            return {"latitude": self.latitude,
                    "longitude": self.longitude,
                    "accuracy": self.accuracy}

    class NetworkConditions(EmbeddedDocument):
        latency_ms = IntField(default=5, required=True)
        download_throughput = IntField(default=500 * 1024, required=True)
        upload_throughput = IntField(default=500 * 1024, required=True)

    class DeviceMetric(EmbeddedDocument):
        device_scale_factor = IntField(default=50, required=True)
        mobile = BooleanField(default=True, required=True)

    geo_location = EmbeddedDocumentField(GeoLocation, default=None)
    network_condition = EmbeddedDocumentField(NetworkConditions, default=None)
    device_metrics = EmbeddedDocumentField(DeviceMetric, default=None)

    def get_webdriver_options_object(self, download_dir='', start_profile_path=''):
        raise NotImplementedError
