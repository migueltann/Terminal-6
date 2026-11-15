"""ItineraryPresenter: turns itinerary objects into data for the web pages."""

from urllib.parse import quote_plus

from models import Itinerary, ItineraryItem, RecommendationSet


class ItineraryPresenter:
    """Prepare plain dicts for the itinerary builder and view templates."""

    # Short label shown on each stop in the itinerary view
    TYPE_LABELS = {"activity": "Activity", "food": "Food",
                   "shopping": "Shopping", "accommodation": "Stay"}

    @staticmethod
    def catalog(recommendation_set: RecommendationSet) -> list[dict]:
        """The approved recommendations the builder can place on days.

        "index" is the item's position in the approved list. The page sends
        these positions back when saving, and the server looks the real
        details up again (see Itinerary.from_selection).
        """
        return [
            {"index": index, "name": item.name, "type": item.item_type,
             "cost": item.cost_sgd, "location": item.location}
            for index, item in enumerate(recommendation_set.approved())
        ]

    def builder_days(self, itinerary: Itinerary,
                     recommendation_set: RecommendationSet) -> list[list[dict]]:
        """Restore a saved itinerary's places and personal entries for editing."""
        catalog = self.catalog(recommendation_set)
        days = []

        for day_index, entries in enumerate(itinerary.selection_for(recommendation_set)):
            restored = []
            for position, entry in enumerate(entries):
                if entry.get("is_custom") is True:
                    # Personal entries are not in the catalog, so give
                    # each one a unique made-up index for the page.
                    item = {"index": f"custom-{day_index}-{position}", "is_custom": True,
                            "name": entry["name"], "type": entry["type"],
                            "cost": 0, "location": ""}
                else:
                    # dict(...) makes a copy, so the catalog is not changed
                    # when the same place is used on more than one day.
                    item = dict(catalog[entry["index"]])

                item.update(meal=entry["meal"], time=entry["time"],
                            duration=entry["duration"])
                restored.append(item)
            days.append(restored)

        return days

    @staticmethod
    def maps_link(item: ItineraryItem, destination: str) -> str:
        """A Google Maps search link for a stop (name + address + city)."""
        query = ", ".join(part for part in (item.name, item.location, destination) if part)
        # quote_plus makes the text safe for a URL (spaces -> "+", "&" -> "%26")
        return "https://www.google.com/maps/search/?api=1&query=" + quote_plus(query)

    def view_days(self, itinerary: Itinerary) -> list[dict]:
        """Everything the itinerary page needs for each day."""
        view_days = []

        for index in range(len(itinerary.days)):
            day_date = itinerary.date_for(index)    # None if no start date was set
            stops = [
                {
                    "time": stop.time, "end": stop.end, "period": stop.period,
                    "label": stop.label, "type": stop.item.item_type,
                    "type_label": self.TYPE_LABELS.get(stop.item.item_type, "Stop"),
                    "name": stop.item.name, "category": stop.item.category,
                    "location": stop.item.location,
                    "description": stop.item.description,
                    "cost": stop.item.cost_sgd, "top_pick": stop.item.top_pick,
                    "maps": self.maps_link(stop.item, itinerary.destination),
                    "note": stop.note,
                }
                for stop in itinerary.schedule(index)
            ]

            view_days.append({
                "number": index + 1,
                # e.g. "Monday, 16 November 2026"
                "date": day_date.strftime("%A, %d %B %Y") if day_date else "",
                "stops": stops,
                # Daytime stops and hotel stays are shown in separate sections.
                "visits": [stop for stop in stops if stop["period"] != "Overnight"],
                "stays": [stop for stop in stops if stop["period"] == "Overnight"],
                "total": itinerary.day_total(index),
                "over": itinerary.is_over_budget(index),
            })

        return view_days