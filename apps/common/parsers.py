"""JSON parser that accepts camelCase and normalises to snake_case."""

from rest_framework.parsers import JSONParser

from apps.common.camel import snakeize


class CamelCaseJSONParser(JSONParser):
    def parse(self, stream, media_type=None, parser_context=None):
        data = super().parse(stream, media_type, parser_context)
        return snakeize(data)
