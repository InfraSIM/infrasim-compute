import os
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
                                "file": os.environ.get(
                                                'TEST_IMAGE_PATH') or "/home/infrasim/jenkins/data/ubuntu14.04.4.qcow2"
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


class IvnConfig(object):

    def __init__(self):
        self.__info = {
            "namespace": [
                "node0ns",
                "node1ns"
            ],
            "ovs": [
                "br-int"
            ],
            "connection": {
                "ns0-einf0": "vint0",
                "ns1-einf0": "vint1"
            },
            "node0ns": {
                "bridges": [
                    {
                        "ifname": "br0",
                        "type": "static",
                        "netmask": "255.255.255.0",
                        "bridge_ports": "ns0-einf0",
                        "address": "192.168.188.91"
                    }
                ],
                "interfaces": [
                    {
                        "ifname": "ns0-einf0",
                        "type": "static",
                        "netmask": "255.255.255.0",
                        "address": "0.0.0.0"
                    }
                ]
            },
            "br-int": {
                "netmask": "255.255.255.0",
                "type": "static",
                "ports": [
                    "vint0",
                    "vint1"
                ],
                "address": "192.168.188.90"
            },
            "node1ns": {
                "bridges": [
                    {
                        "ifname": "br0",
                        "type": "static",
                        "netmask": "255.255.255.0",
                        "bridge_ports": "ns1-einf0",
                        "address": "192.168.188.92"
                    }
                ],
                "interfaces": [
                    {
                        "ifname": "ns1-einf0",
                        "type": "static",
                        "netmask": "255.255.255.0",
                        "address": "0.0.0.0"
                    }
                ]
            },
            "portforward": {
                "rules": [
                    "192.168.188.91 5901 15901",
                    "192.168.188.92 5901 25901",
                    "192.168.188.91 8022 18022",
                    "192.168.188.92 8022 28022"
                ],
                "io_interfaces": [
                    "ens160",
                    "br-int"
                ]
            }
        }

    def get_ivn_info(self):
        return self.__info
