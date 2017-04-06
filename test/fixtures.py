
from infrasim import helper

class FakeConfig(object):
    def __init__(self):
        self.__node_info = {
            "name": "test",
            "type": "dell_r730",
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
                        "type": "ahci",
                        "max_drive_per_controller": 6,
                        "use_jbod": "true",
                        "use_msi": "true",
                        "max_cmds": 1024,
                        "max_sge": 128,
                        "drives": [
                            {
                                "size": 8
                            }
			]		
                    }
                ],
                "networks": [
                    {
                        "network_mode": "nat",
                        "device": "e1000",
			"network_name": "dummy0"
                    }
                ]
            }
        }

    def get_node_info(self):
        return self.__node_info
