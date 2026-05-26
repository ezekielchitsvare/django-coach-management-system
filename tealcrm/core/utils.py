from urllib.parse import urlparse

from django.utils.http import url_has_allowed_host_and_scheme


def get_safe_next_url(request):
    next_url = request.POST.get('next') or request.GET.get('next')

    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url

    return None


def get_safe_referer_url(request):
    referer = request.META.get('HTTP_REFERER')

    if referer and url_has_allowed_host_and_scheme(
        referer,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return referer

    return None


def get_safe_return_url(request, fallback_url):
    for candidate in (get_safe_next_url(request), get_safe_referer_url(request)):
        if not candidate:
            continue

        candidate_path = urlparse(candidate).path
        if candidate_path == request.path:
            continue

        return candidate

    return fallback_url
