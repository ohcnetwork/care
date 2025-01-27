from drf_spectacular.utils import extend_schema, extend_schema_view


def generate_swagger_schema_decorator(cls):
    if not hasattr(cls, "tags"):
        cls.tags = [cls.__name__.replace("ViewSet", "")]

    base_actions = {
        "create": {
            "request": cls.pydantic_model,
            "responses": {200: cls.pydantic_read_model or cls.pydantic_model},
        },
        "update": {
            "request": cls.pydantic_update_model or cls.pydantic_model,
            "responses": {200: cls.pydantic_read_model or cls.pydantic_model},
        },
        "list": {"responses": {200: cls.pydantic_read_model or cls.pydantic_model}},
        "retrieve": {
            "responses": {
                200: cls.pydantic_retrieve_model
                or cls.pydantic_read_model
                or cls.pydantic_model
            }
        },
        "destroy": {"responses": {204: None}},
    }

    for action in base_actions.values():
        action["tags"] = cls.tags

    extra_actions = {
        action.url_path: {"tags": cls.tags}
        for action in cls.get_extra_actions()
        if hasattr(action, "url_path")
    }

    all_actions = {**base_actions, **extra_actions}

    schema_dict = {
        name: extend_schema(**params)
        for name, params in all_actions.items()
        if hasattr(cls, name) and callable(getattr(cls, name))
    }

    return extend_schema_view(**schema_dict)(cls)
