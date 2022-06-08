import enum


class BaseAssetIntegration:
    def __init__(self, type, meta):
        self.type = type
        self.meta = meta

    def get_type(self):
        return self.type

    def handle_action(self, action):
        pass
