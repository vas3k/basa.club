class GeoCookieMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.country_id = request.COOKIES.get("country") or "everywhere"
        request.city_id = request.COOKIES.get("city") or "everywhere"

        response = self.get_response(request)

        if "country" not in request.COOKIES:
            response.set_cookie("country", request.country_id, max_age=365 * 24 * 60 * 60, samesite="Lax", path="/")
            response.set_cookie("city", request.city_id, max_age=365 * 24 * 60 * 60, samesite="Lax", path="/")
        return response
