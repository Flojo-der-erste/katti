import datetime

from mongoengine import Document, StringField, IntField, DateTimeField


class ASN(Document):
    meta = {'collection': 'max_mind_asn',
            'db_alias': 'Katti',
            'indexes': [{'fields': ['autonomous_system_organization']},
                        {'fields': ['autonomous_system_number']}]}

    autonomous_system_organization = StringField()
    autonomous_system_number = IntField()
    last_seen = DateTimeField()

    @staticmethod
    def get_asn(autonomous_system_number, autonomous_system_organization):
        try:
            asn_object = ASN.objects.get(autonomous_system_number=autonomous_system_number)
        except Exception:
            asn_object = ASN.objects(autonomous_system_number=autonomous_system_number).modify(__raw__={'$setOnInsert': {'autonomous_system_organization': autonomous_system_organization}},
                                                                                         upsert=True,
                                                                                         new=True)
        return asn_object