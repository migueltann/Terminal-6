def rank_recommendations(items, user_inputs):
    """Put stronger matches near the top of the final result."""

    def score(item):
        points = 0

        return points