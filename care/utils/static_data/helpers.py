import re

from redis_om.model.token_escaper import TokenEscaper

token_escaper = TokenEscaper(re.compile(r"[,.<>{}\[\]\\\"\':;!@#$%^&*()\-+=~\/ ]"))


def query_builder(query: str) -> str:
    """
    Builds a query for redis full text search from a given query string.
    """
    words = query.strip().rsplit(maxsplit=3)
    return f"{'* '.join([token_escaper.escape(word) for word in words])}*"
