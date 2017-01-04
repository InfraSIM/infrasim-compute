
from infrasim import helper

class FakeConfig(object):
    def __init__(self):
        self.__node_info = {
            "name": "test",
            "type": "quanta_d51",
            "compute": {
                "kvm_enabled": helper.check_kvm_existence(),
                "cpu": {
                    "quantities": 2,
                    "type": "Haswell"
                },
                "memory": {
                    "size": 1024
                },
                "storage_backend": [
                    {
                        "controller": {
                            "type": "ahci",
                            "max_drive_per_controller": 8,
                            "drives": [
                                {
                                    "size": 8
                                }
                            ]
                        }
                    }
                ],
                "networks": [
                    {
                        "network_mode": "nat",
                        "device": "e1000"
                    }
                ]
            }
        }

    def get_node_info(self):
        return self.__node_info
