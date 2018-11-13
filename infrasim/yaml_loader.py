import yaml
import os


def longhex_presenter(dumper, data):
    if (data > 0xffffffff):
        return dumper.represent_scalar(u'tag:yaml.org,2002:int', "0x{:02x}".format(data))
    return dumper.represent_scalar(u'tag:yaml.org,2002:int', "{}".format(data))


yaml.add_representer(long, longhex_presenter)
yaml.add_representer(int, longhex_presenter)


class YAMLLoader(yaml.Loader):
    def __init__(self, stream):
        super(YAMLLoader, self).__init__(stream)
        self._root = os.path.split(stream.name)[0]
        self.add_constructor('!include', self._include)

    def _include(self, *args):
        loader = args[0]
        node = args[1]
        filename = os.path.join(self._root, loader.construct_scalar(node))
        with open(filename, 'r') as f:
            return yaml.load(f, YAMLLoader)
