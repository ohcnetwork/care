def get_psql_search_tokens(text, operator="&"):
    return f" {operator} ".join([f"{word}:*" for word in text.strip().split(" ")])
