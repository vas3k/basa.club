from django.conf import settings

from geo.models import GeoCountry


def geo(request):
    countries = list(GeoCountry.objects.prefetch_related("cities"))

    current_country = None
    current_city = None
    cities = []
    for country in countries:
        if country.id == request.country_id:
            current_country = country
            cities = list(country.cities.all())
            for city in cities:
                if city.id == request.city_id:
                    current_city = city
            break

    return {
        "countries": [country for country in countries if country.id != settings.ONLINE_COUNTRY_ID],
        "online_country": next((country for country in countries if country.id == settings.ONLINE_COUNTRY_ID), None),
        "cities": cities,
        "current_country": current_country,
        "current_city": current_city,
    }
