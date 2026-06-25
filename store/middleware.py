from django.contrib.auth import logout, get_user_model

User = get_user_model()

class FixStringUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # If request.user is a string, log them out immediately
        if request.user.is_authenticated and not isinstance(request.user, User):
            logout(request)
        return self.get_response(request)