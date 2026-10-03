from django.shortcuts import redirect

from users.models import User


def view_profile_action(request, user: User, **context):
    return redirect("user_profile", slug=user.slug)
