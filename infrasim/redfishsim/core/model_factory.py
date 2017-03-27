class ModelFactory(object):
    """
    Factory to generate flask models
    """
    def __init__(self, name=''):
        self.data = None
        self.name = name

    def start_record(self, data):
        pass

    def end_record(self, data):
        self.data = data.copy()

    def __getattr__(self, item):
        if self.data and item in self.data:
            return self.data[item]
        raise AttributeError("{0}({1} has no attribute '{2}'".format(self, self.name, item))
