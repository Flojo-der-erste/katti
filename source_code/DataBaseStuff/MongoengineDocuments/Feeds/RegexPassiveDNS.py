from mongoengine import EmbeddedDocument, StringField, ListField, ValidationError


class RegexPassiveDNS(EmbeddedDocument):
    regex_tag_name = StringField(required=True)
    regex_list = ListField(default=[], required=True)

    def clean(self):
        for regex in self.regex_list:
            if not isinstance(regex, str):
                raise ValidationError('Only strings are accepted.')
        super().clean()

