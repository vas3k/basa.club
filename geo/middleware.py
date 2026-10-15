from django.utils.deprecation import MiddlewareMixin


class GeoMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        request.country_id = view_kwargs.get("country") or "everywhere"
        request.city_id = view_kwargs.get("city") or "everywhere"

    def process_response(self, request, response):
        if "country" in request.COOKIES:
            response.delete_cookie("country", path="/", samesite="Lax")
        if "city" in request.COOKIES:
            response.delete_cookie("city", path="/", samesite="Lax")
        return response
