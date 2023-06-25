from drf_spectacular.openapi import AutoSchema as SpectacularAutoSchema


class AutoSchema(SpectacularAutoSchema):
    def get_tags(self):
        tokenized_path = self._tokenize_path()
        # use last non-parameter path part as default tag
        return [tokenized_path[-1]]
