"""Checks that a destination typed by the user is a real country or city."""

import difflib
import re
import unicodedata
from typing import Optional

try:
    import geonamescache
except ImportError:  # keeps the program running if the library is missing
    geonamescache = None


class DestinationValidator:
    """Validates destinations against the geonamescache country and city lists."""

    def __init__(self) -> None:
        # country code -> display name, e.g. "JP" -> "Japan"
        self.__country_names: dict[str, str] = {}
        # normalised name or ISO code -> country code, e.g. "japan" -> "JP"
        self.__country_lookup: dict[str, str] = {}
        # normalised city -> {country code: (population, city name)}
        self.__city_lookup: dict[str, dict[str, tuple[int, str]]] = {}
        self.__load_geo_data()

    @staticmethod
    def _normalise(text: str) -> str:
        """Lowercase and remove accents and punctuation from names."""
        text = unicodedata.normalize("NFKD", str(text))
        text = "".join(char for char in text if not unicodedata.combining(char))
        return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()

    def __load_geo_data(self) -> None:
        """Build the lookup tables from geonamescache once, when the object is created."""
        if geonamescache is None:
            return

        gc = geonamescache.GeonamesCache()

        for code, country in gc.get_countries().items():
            self.__country_names[code] = country["name"]
            for key in (country["name"], country["iso"], country["iso3"]):
                self.__country_lookup[self._normalise(key)] = code

        for city in gc.get_cities().values():
            key = self._normalise(city["name"])
            if not key:
                continue
            by_country = self.__city_lookup.setdefault(key, {})
            code = city["countrycode"]
            if code not in by_country or city["population"] > by_country[code][0]:
                by_country[code] = (city["population"], city["name"])

    @staticmethod
    def __suggest(key: str, pool: list[str]) -> Optional[str]:
        """Return the closest known name to a mistyped one, or None."""
        matches = difflib.get_close_matches(key, pool, n=1, cutoff=0.75)
        return matches[0] if matches else None

    def __validate_single(self, text: str) -> tuple[Optional[str], Optional[str]]:
        """One part only: it must be a country (name or code) or a city."""
        names, countries, cities = self.__country_names, self.__country_lookup, self.__city_lookup
        key = self._normalise(text)

        if key in countries:
            return names[countries[key]], None

        if key in cities:
            # If several countries have this city, use the most populous one.
            code, (_, city) = max(cities[key].items(), key=lambda item: item[1][0])
            if self._normalise(city) == self._normalise(names[code]):
                return city, None
            return f"{city}, {names[code]}", None

        message = f"'{text}' is not a valid country or city. Please enter a valid country or city."
        guess = self.__suggest(key, list(countries) + list(cities))
        if guess:
            name = (names[countries[guess]] if guess in countries
                    else next(iter(cities[guess].values()))[1])
            message += f" Did you mean {name}?"
        return None, message

    def __validate_city_country(self, city_text: str, country_text: str) -> tuple[Optional[str], Optional[str]]:
        """City + country: the country (last part) and the city must both be real."""
        names, countries, cities = self.__country_names, self.__country_lookup, self.__city_lookup
        country_key = self._normalise(country_text)

        if country_key not in countries:
            message = f"'{country_text}' is not a recognised country."
            guess = self.__suggest(country_key, list(countries))
            if guess:
                message += f" Did you mean {names[countries[guess]]}?"
            return None, message

        code = countries[country_key]
        country = names[code]
        city_key = self._normalise(city_text)

        if city_key == self._normalise(country):
            return country, None
        if city_key in cities and code in cities[city_key]:
            return f"{cities[city_key][code][1]}, {country}", None

        message = f"Could not find '{city_text}' in {country}."
        in_country = [key for key, value in cities.items() if code in value]
        guess = self.__suggest(city_key, in_country)
        if guess:
            message += f" Did you mean {cities[guess][code][1]}?"
        return None, message