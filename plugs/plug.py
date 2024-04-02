class Plug:
    """
    Abstraction of a plugin
    """

    def __init__(self, name, package_name, version, configs):
        self.name = name
        self.package_name = package_name
        self.version = version
        self.configs = configs
