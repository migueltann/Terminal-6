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