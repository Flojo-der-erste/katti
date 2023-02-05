import ipaddress
from urllib.parse import urlsplit, parse_qs
import vt
from mongoengine import EmbeddedDocument, StringField, BooleanField, DictField, DynamicField, \
    IntField


class URL(EmbeddedDocument):
    meta = {'abstract': True}
    url = StringField()
    domain = StringField()
    url_only_with_path = StringField()
    vt_id = StringField()
    query = DictField()
    fragment = DynamicField()

    @classmethod
    def build(cls, url):
        url_parser_obj = urlsplit(url)
        new_url = cls(url=url)
        new_url.url_only_with_path = f'{url_parser_obj.scheme}://{url_parser_obj.netloc}{url_parser_obj.path}'
        new_url.query = parse_qs(url_parser_obj.query) if len(parse_qs(url_parser_obj.query)) > 0 else None
        new_url.vt_id = vt.url_id(new_url.url_only_with_path)
        new_url.domain = url_parser_obj.hostname
        new_url.fragment = url_parser_obj.fragment if not url_parser_obj.fragment == '' else None

        if new_url.query: #$ is reserved in MonogoDB
            x = {}
            for key in new_url.query:
                try:
                    x.update({key.replace('$', '<dollar>'): new_url.query[key]})
                except Exception:
                    pass
            new_url.query = x
        return new_url


class Link(URL):
    type = StringField(choices=['intern', 'extern', 'social_media', 'unrated'], default='unrated')
    malicious = BooleanField(default=False)


class SeleniumWireRequestURL(URL):
    ip_str = StringField()
    ipv4_int = IntField()
    port = IntField()

    def set_ip(self, ip_str):
        self.ip_str = ip_str
        try:
            ipv4_int = int(ipaddress.IPv4Address(ip_str))
        except Exception:
            pass

