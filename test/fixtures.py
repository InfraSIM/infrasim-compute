
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
            },
            "monitor": {}
        }

    def get_node_info(self):
        return self.__node_info

class NvmeConfig(object):
    def __init__(self):
        self.__node_info = {
            "name": "nvme",
            "type": "dell_r730xd",
            "compute": {
                "kvm_enabled": helper.check_kvm_existence(),
                "boot": {
                    "boot_order": "c"
                },
                "cpu": {
                    "quantities": 4,
                    "feature": "+vmx",
                    "type": "Haswell"
                },
                "memory": {
                    "size": 4096
                },
                "storage_backend": [
                    {
                        "type": "ahci",
                        "max_drive_per_controller": 6,
                        "drives": [
                            {
                                "size": 40,
                                "model": "SATADOM",
                                "serial": "20160518AA851134100",
                                "file": "/home/infrasim/jenkins/data/ubuntu14.04.4.qcow2"
                            }
                        ]
                    },
                    {
                        "cmb_size_mb": 2,
                        "drives": [
                            {
                                "size": 8
                            }
                        ],
                        "lba_index": 0,
                        "namespaces": 2,
                        "serial": "0400001C1FF9",
                        "type": "nvme",
                        "oncs": "0xf"

                    },
                    {
                        "cmb_size_mb": 2,
                        "drives": [
                            {
                                "size": 8
                            }
                        ],
                        "lba_index": 0,
                        "namespaces": 3,
                        "serial": "0400001C6BB4",
                        "type": "nvme",
                        "oncs": "0xf"
                    }
                ],
                "networks": [
                    {
                        "network_mode": "nat",
                        "device": "e1000",
                        "network_name": "dummy0"
                    }
                ]
            },
            "sol_enable": "true"
        }

    def get_node_info(self):
        return self.__node_info
