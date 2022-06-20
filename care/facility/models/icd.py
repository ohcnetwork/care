class ICDDisease:
    def __init__(self, **kwargs):
        for field in ('id', 'name', 'reference_url'):
            setattr(self, field, kwargs.get(field, None))
