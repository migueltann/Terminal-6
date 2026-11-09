"""Stores recommendation sets using JSON and CSV files."""

import json
import os

from .recommendation_repository import RecommendationRepository


class JsonCsvRepository(RecommendationRepository):
    """File-based implementation of recommendation storage."""

    def __init__(self, data_dir: str = "data"):
        self._data_dir = data_dir
        self._index_file = os.path.join(
            data_dir,
            "recommendation_sets.json",
        )

    