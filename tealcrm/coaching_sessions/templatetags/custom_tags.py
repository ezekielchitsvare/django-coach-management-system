from django import template
from django.http import QueryDict

register = template.Library()


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, [])


@register.filter
def current_url(request):
    query_dict = QueryDict(request.META.get('QUERY_STRING', ''), mutable=True)
    query_dict.pop('next', None)

    query_string = query_dict.urlencode()
    if query_string:
        return f'{request.path}?{query_string}'

    return request.path
