from mongoengine import EmbeddedDocument, IntField, BooleanField, FloatField, ObjectIdField, EmbeddedDocumentListField



class ColisionSpider():
    pass


class SpiderNode(EmbeddedDocument):
    previous_bundle = ObjectIdField()
    creation_deep = IntField()


class SpiderMode(EmbeddedDocument):
    first_spider_mode = BooleanField(required=True)
    current_deep = IntField()
    nodes = EmbeddedDocumentListField(SpiderNode)


class SpiderConfig(EmbeddedDocument):
    intern_links = BooleanField(default=True)
    extern_links = BooleanField(default=False)
    social_media_links = BooleanField(default=False)
    add_to_crawling_url_set = BooleanField(default=False)
    max_deep = IntField(min_value=0, default=0) # 0: infinity

    average_index = FloatField(min_value=0.0, max_value=1.0, default=1.0)

    """
    In hours.
    -1: Never crawl an url again
    0: Not allowed, Infinity Dangerous    
    """
