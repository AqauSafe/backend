"""JSON renderer that presents snake_case internals as camelCase."""

from rest_framework.renderers import JSONRenderer

from apps.common.camel import camelize


class CamelCaseJSONRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        return super().render(camelize(data), accepted_media_type, renderer_context)
