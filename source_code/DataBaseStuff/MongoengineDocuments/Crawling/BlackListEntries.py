import datetime

from mongoengine import Document, StringField, DateTimeField, Q


class BlackListEntry(Document):
    meta = {'collection': 'crawling_blacklists',
            'allow_inheritance': True}
    ttl = DateTimeField(required=True)
    description = StringField()
    reason = StringField()


class URLBlackListEntry(BlackListEntry):
    url = StringField()
    domain = StringField()

    @staticmethod
    def is_blacklisted(url:str = None, domain: str = None) -> bool:
        if url and domain:
            result = list(URLBlackListEntry.objects(Q(url=url) | Q(domain=domain)))
        elif url:
            result = list(URLBlackListEntry.objects(url=url))
        else:
            result = list(URLBlackListEntry.objects(domain=domain))
        if len(result) > 0:
            return True
        else:
            return False



class IPBlackListEntry(BlackListEntry):
    ip = StringField()

    @staticmethod
    def is_blacklisted(ooi)-> bool:
        pass
