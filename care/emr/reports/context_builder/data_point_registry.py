class DataPointRegistry:
    _data_points: dict[str, dict] = {}
    _model_mapping: dict[str, dict] = {}

    @classmethod
    def register(cls, data_point):
        cls._data_points[data_point.__slug__] = data_point

    @classmethod
    def get(cls, slug: str):
        return cls._data_points.get(slug)

    @classmethod
    def get_all(cls):
        return cls._data_points.copy()

    @classmethod
    def is_registered(cls, slug: str) -> bool:
        return slug in cls._data_points

    @classmethod
    def clear(cls):
        cls._data_points.clear()

    @classmethod
    def get_contexts_by_model(cls, model):
        return [
            context.__slug__
            for context in cls._data_points.values()
            if context.__associating_model__ == model
        ]
