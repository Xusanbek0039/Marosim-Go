class ApiSecurityHeadersMiddleware:
    """API responses carry personal data: never cache them and never let them be framed or sniffed."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith("/api/"):
            response["Cache-Control"] = "no-store"
            response["Pragma"] = "no-cache"
            response.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
            if not request.path.startswith("/api/v1/docs/"):
                response.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
        return response
