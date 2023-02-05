from mongoengine import EmbeddedDocument, StringField, IntField


class Interval(EmbeddedDocument):
    period = StringField(choices=['day', 'seconds'], default='day')
    every = IntField(min_value=1, default=1)


class CronTab(EmbeddedDocument):
    minute = StringField(default='*', required=True)
    hour = StringField(default='*', required=True)
    day_of_week = StringField(default='*', required=True)
    day_of_month = StringField(default='*', required=True)
    month_of_year = StringField(default='*', required=True)

    def to_string(self):
        return f'{self.minute} {self.hour} {self.day_of_week} {self.day_of_month} {self.month_of_year}'