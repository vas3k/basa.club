from django.http import JsonResponse
from django.shortcuts import render

from vas3k_base.exceptions import ApiException, ClubException


class ExceptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        if isinstance(exception, ApiException):
            return JsonResponse({
                "error": {
                    "code": exception.code,
                    "title": exception.title,
                    "message": exception.message,
                    "data": exception.data,
                }
            }, status=400)

        if isinstance(exception, ClubException):
            return render(request, "error.html", {
                "code": exception.code,
                "title": exception.title,
                "message": exception.message,
                "data": exception.data,
            }, status=400)
