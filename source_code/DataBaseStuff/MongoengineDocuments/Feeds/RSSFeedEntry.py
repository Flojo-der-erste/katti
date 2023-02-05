from mongoengine import URLField, StringField, DateTimeField

from DataBaseStuff.MongoengineDocuments.Feeds.BaseFeedEntry import BaseFeedEntry


class RSSFeedEntry(BaseFeedEntry):
    meta = {'collection': 'rss_entries',
            'db_alias': 'Feeds',
            'indexes': [{'fields': ['feed', 'title', 'url', 'end_valid'],
                         'name': 'main_rss'}]}

    url = URLField(required=True)
    summary = StringField()
    title = StringField()
    published = DateTimeField()
    last_seen = DateTimeField()

    def _build_update_dict_for_update_one(self) -> dict:
        return {'$setOnInsert': {'summary': self.summary,
                                 'title': self.title,
                                 'published': self.published},
                '$set': {'last_seen': self.last_seen}}

    def _build_filter_dict_for_update_one(self) -> dict:
        return {'url': self.url}

    def get_domain(self):
        pass
