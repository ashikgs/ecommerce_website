from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()

class SafeModelBackend(ModelBackend):
    """
    Converts a session‑stored string (username) into a User instance.
    """
    def get_user(self, user_id):
        try:
            if isinstance(user_id, str):
                # user_id is a username string – return the actual user
                return User.objects.get(username=user_id)
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None