from django.conf import settings
from rest_framework_jwt.authentication import JSONWebTokenAuthentication

JWT_COOKIE_NAME = settings.JWT_AUTH.get("JWT_AUTH_COOKIE")


class JWTMiddleware:
    """
    Enable djangorestframework-jwt authentication also for non
    rest framework requests like normal django views and graphql
    requests.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def process_view(self, request, view_func, view_args, view_kwargs):
        # token should be either in http headers or cookie..
        token = request.META.get("HTTP_AUTHORIZATION", "")
        if not token.startswith("JWT") and JWT_COOKIE_NAME not in request.COOKIES:
            return
        jwt_auth = JSONWebTokenAuthentication()
        auth = None
        try:
            auth = jwt_auth.authenticate(request)
        except Exception:
            return
        if auth is not None:
            request.user = auth[0]

    def __call__(self, request):
        return self.get_response(request)
