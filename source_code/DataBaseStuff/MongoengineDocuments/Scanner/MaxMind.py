from mongoengine import Document, URLField, StringField


class MaxMindConfig(Document):
    country_db_name = StringField()