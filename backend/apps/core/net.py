from django.conf import settings


def client_ip(request) -> str | None:
    """Client IP, trusting ``X-Forwarded-For`` only for the configured number of proxies."""
    remote = request.META.get("REMOTE_ADDR")
    num_proxies = settings.NUM_PROXIES
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if num_proxies and forwarded:
        addrs = [a.strip() for a in forwarded.split(",") if a.strip()]
        if addrs:
            return addrs[-min(num_proxies, len(addrs))]
    return remote


def user_agent(request) -> str:
    return (request.META.get("HTTP_USER_AGENT") or "")[:255]
