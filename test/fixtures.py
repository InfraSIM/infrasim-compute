import os
from infrasim import helper
from collections import OrderedDict
image = os.environ.get("TEST_IMAGE_PATH") or "/home/infrasim/jenkins/data/ubuntu18.04.qcow2"
a_boot_image = os.environ.get("TEST_IMAGE_PATH") or "/home/infrasim/jenkins/data/ubuntu18.04.qcow2"
b_boot_image = "/home/infrasim/jenkins/data/ubuntu18.04_b.qcow2"

cloud_img_ubuntu_16_04 = "/home/infrasim/jenkins/data/ubuntu-16.04-server-cloudimg-amd64-120G.org.bak"
cloud_img_ubuntu_18_04 = "/home/infrasim/jenkins/data/ubuntu-18.04-lts-server-cloudimg-amd64.img"


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
                    "size": 4096
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
                                "size": 16
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
                                "file": image
                            }
                        ]
                    },
                    {
                        "cmb_size_mb": 1,
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
                        "cmb_size_mb": 1,
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


class ChassisConfig(object):

    def __init__(self):

        self.__chassis_info = {
            "name": "chassis_test",
            "type": "dell_r730",
            "data": {
                "psu1_sn": "BEAF-BEAF-BEAF",
                "psnt_pn": "WHAT_EVER_PN",
                "psu1_pn": "A380-B737-C909",
                "psu2_pn": "A380-B747-C909",
                "pn": "WHAT_EVER_PN",
                "sn": "WHAT_EVER_SN",
            },
            "nodes": [
                {
                    "namespace": "node0ns",
                    "bmc": {},
                    "compute": {
                        "memory": {
                            "size": 2048
                        },
                        "boot": {
                            "boot_order": "c"
                        },
                        "cpu": {
                            "quantities": 2,
                            "type": "Haswell"
                        },

                        "storage_backend": [
                            {
                                "type": "ahci",
                                "drives": [
                                    {
                                        "model": "SATADOM",
                                    }
                                ],
                                "max_drive_per_controller": 6
                            },
                            {
                                "slot_range": "0-16",
                                "type": "lsisas3008",
                                "sas_address": 5874503300116285184,
                                "max_drive_per_controller": 36
                            }
                        ],

                        "networks": [
                            {
                                "device": "e1000",
                                "network_mode": "nat",
                                "network_name": "br0",
                                "port_forward": [
                                    {
                                        "outside": 8022,
                                        "inside": 22,
                                        "protocal": "tcp"
                                    }
                                ]
                            }
                        ]
                    }
                },
                {
                    "namespace": "node1ns",
                    "bmc": {},
                    "compute": {
                        "memory": {
                            "size": 2048
                        },
                        "boot": {
                            "boot_order": "c"
                        },
                        "cpu": {
                            "quantities": 2,
                            "type": "Haswell"
                        },
                        "storage_backend": [
                            {
                                "type": "ahci",
                                "drives": [
                                    {
                                        "model": "SATADOM",
                                    }
                                ],
                                "max_drive_per_controller": 6
                            },
                            {
                                "slot_range": "0-16",
                                "type": "lsisas3008",
                                "sas_address": 5874503300119285184,
                                "max_drive_per_controller": 36
                            }
                        ],

                        "networks": [
                            {
                                "device": "e1000",
                                "network_mode": "nat",
                                "network_name": "br0",
                                "port_forward": [
                                    {
                                        "outside": 8022,
                                        "inside": 22,
                                        "protocal": "tcp"
                                    }
                                ]
                            }
                        ]
                    }
                }
            ],

            "slots": [
                {
                    "chassis_slot": 17,
                    "format": "raw",
                    "cache": "writeback",
                    "share-rw": "true",
                    "file": "/tmp/disk-nvme-3.img",
                    "serial": "B4SSXT2FKAM4",
                    "type": "nvme",
                    "id": "nvme-3",
                    "if": "none"
                },
                {
                    "product": "HUSMM114_CLAR400",
                    "chassis_slot": 0,
                    "vendor": "HITACHI",
                    "format": "raw",
                    "share-rw": "true",
                    "version": "B29C",
                    "file": "/tmp/sas_0.img",
                    "serial": "Z4C03DFX",
                    "wwn": 5764824129059367281,
                    "rotation": 1,
                    "channel": 0,
                    "size": 2
                },
            ]
        }

    def get_chassis_info(self):
        return self.__chassis_info


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


class FlowList(list):
    pass


class CloudNetworkConfig(object):
    def __init__(self):
        self.__info = OrderedDict([
            ("version", 1),
            ("config", [
                OrderedDict([
                    ("type", "physical"),
                    ("name", "enp0s3"),
                    ("mac_address", {}),
                    ("subnets", [
                        {"type": "dhcp"}
                    ])
                ]),
                OrderedDict([
                    ("type", "physical"),
                    ("name", "eth0"),
                    ("mac_address", {}),
                    ("subnets", [
                        OrderedDict([
                            ("type", "static"),
                            ("address", {}),
                            ("netmask", "255.255.255.0"),
                            ("routes", [
                                OrderedDict([
                                    ("network", "0.0.0.0"),
                                    ("netmask", "0.0.0.0"),
                                    ("gateway", {})
                                ])
                            ]
                            )
                        ]
                        )])]),
                OrderedDict([
                    ("type", "nameserver"),
                    ("address", FlowList([{}, "8.8.8.8", "8.8.4.4"])),
                    ("search", FlowList(["example.com", "foo.biz", "bar.info"]))
                ])
            ])
        ])

    def get_network_info(self):
        return self.__info
