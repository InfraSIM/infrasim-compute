'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
import unittest
import os
import time
import yaml
from infrasim import model
from infrasim import helper
import paramiko
from test import fixtures


"""
For each node type, do a test to verify KCS function and SMBIOS data integrity.
Node type includes:
    - dell_c6320
    - dell_r630
    - dell_r730
    - dell_r730xd
    - quanta_d51
    - quanta_t41
    - s2600kp
    - s2600tp
    - s2600wtt

Test KCS function
    - local fru can work
    - local lan can work
    - local sensor can work
    - local sel can work
    - local sdr can work
    - local user can work
Test SMBIOS data
    - verify system information "Product Name" and "Manufacturer"
"""


conf = {}
tmp_conf_file = "/tmp/test.yml"
old_path = os.environ.get("PATH")
new_path = "{}/bin:{}".format(os.environ.get("PYTHONPATH"), old_path)


def setup_module():
    os.environ["PATH"] = new_path


def teardown_module():
    global conf
    if conf:
        stop_node()
    os.environ["PATH"] = old_path


def start_node(node_type):
    global conf
    global tmp_conf_file

    fake_config = fixtures.FakeConfig()
    conf = fake_config.get_node_info()
    conf["type"] = node_type
    # Speed up booting by going to hdd directly
    conf["compute"]["boot"]["boot_order"] = "c"
    conf["compute"]["storage_backend"] = [{
        "type": "ahci",
        "max_drive_per_controller": 6,
        "drives": [{"size": 8, "file": fixtures.image}]
    }]

    with open(tmp_conf_file, "w") as yaml_file:
        yaml.dump(conf, yaml_file, default_flow_style=False)

    node = model.CNode(conf)
    node.init()
    node.precheck()
    node.start()
    node.wait_node_up()
    helper.port_forward(node)

    global ssh
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    paramiko.util.log_to_file("filename.log")
    helper.try_func(600, paramiko.SSHClient.connect, ssh, "127.0.0.1",
                    port=2222, username="root", password="root", timeout=300)
    time.sleep(5)


def stop_node():
    global conf
    global tmp_conf_file

    ssh.close()
    node = model.CNode(conf)
    node.init()
    node.stop()
    node.terminate_workspace()
    conf = {}
    if os.path.exists(tmp_conf_file):
        os.unlink(tmp_conf_file)
    time.sleep(5)


def verify_qemu_local_fru(expect):
    stdin, stdout, stderr = ssh.exec_command("ipmitool fru print")
    lines = recv_ssh_channel(stdout.channel, 4096)

    assert expect in lines


def verify_qemu_local_lan(expect):
    stdin, stdout, stderr = ssh.exec_command("ipmitool lan print")
    lines = recv_ssh_channel(stdout.channel, 2048)

    assert expect in lines


def verify_qemu_local_sensor(expect):
    stdin, stdout, stderr = ssh.exec_command("ipmitool sensor list")
    lines = recv_ssh_channel(stdout.channel, 20480)

    assert expect in lines


def verify_qemu_local_sdr(expect):
    stdin, stdout, stderr = ssh.exec_command("ipmitool sdr list")
    lines = recv_ssh_channel(stdout.channel, 20480)

    assert expect in lines


def verify_qemu_local_sel(expect):
    stdin, stdout, stderr = ssh.exec_command("ipmitool sel clear")
    lines = recv_ssh_channel(stdout.channel, 20480)

    stdin, stdout, stderr = ssh.exec_command("ipmitool sel list")
    lines = recv_ssh_channel(stdout.channel, 20480)

    assert expect in lines


def verify_qemu_local_user(expect):
    stdin, stdout, stderr = ssh.exec_command("ipmitool user list")
    lines = recv_ssh_channel(stdout.channel, 20480)

    assert expect in lines


def verify_smbios_data(expect_mfg, expect_product_name):
    stdin, stdout, stderr = ssh.exec_command("dmidecode -t1")
    lines = recv_ssh_channel(stdout.channel, 20480)

    assert expect_mfg in lines
    assert expect_product_name in lines


def recv_ssh_channel(channel, max_buff_size):
    # Make sure remote process succeeded
    while not channel.exit_status_ready():
        pass

    # Assume Transport has enough buffer to hold receiving data
    assert channel.recv_exit_status() == 0

    while not channel.recv_ready():
        pass

    lines = ""
    while True:
        temp = channel.recv(max_buff_size)
        if len(temp) == 0:
            break
        lines += temp
    print lines

    return lines


@unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
class test_quanta_d51(unittest.TestCase):

    @classmethod
    @unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
    def setUpClass(cls):
        start_node(node_type="quanta_d51")

    @classmethod
    @unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
    def tearDownClass(cls):
        stop_node()

    def test_qemu_local_fru(self):
        verify_qemu_local_fru(expect="QTFCJ052806D1")

    def test_qemu_local_lan(self):
        verify_qemu_local_lan(expect="Auth Type")

    def test_qemu_local_sensor(self):
        verify_qemu_local_sensor(expect="Temp_PCI_Inlet1")

    def test_qemu_local_sdr(self):
        verify_qemu_local_sdr(expect="Temp_PCI_Inlet1")

    def test_qemu_local_sel(self):
        verify_qemu_local_sel(expect="Log area reset/cleared")

    def test_qemu_local_user(self):
        verify_qemu_local_user(expect="ADMINISTRATOR")

    def test_smbios_data(self):
        verify_smbios_data(expect_mfg="Manufacturer: Quanta Computer Inc",
                           expect_product_name="Product Name: D51B-2U (dual 10G LoM)")


@unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
class test_quanta_t41(unittest.TestCase):

    @classmethod
    @unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
    def setUpClass(cls):
        start_node(node_type="quanta_t41")

    @classmethod
    @unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
    def tearDownClass(cls):
        stop_node()

    def test_qemu_local_fru(self):
        verify_qemu_local_fru(expect="WKJ51100867")

    def test_qemu_local_lan(self):
        verify_qemu_local_lan(expect="Auth Type")

    def test_qemu_local_sensor(self):
        verify_qemu_local_sensor(expect="Pwr_Node")

    def test_qemu_local_sdr(self):
        verify_qemu_local_sdr(expect="Pwr_Node")

    def test_qemu_local_sel(self):
        verify_qemu_local_sel(expect="Log area reset/cleared")

    def test_qemu_local_user(self):
        verify_qemu_local_user(expect="ADMINISTRATOR")

    def test_smbios_data(self):
        verify_smbios_data(expect_mfg="Manufacturer: Quanta Computer Inc",
                           expect_product_name="Product Name: QuantaPlex T41S-2U")


@unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
class test_s2600kp(unittest.TestCase):

    @classmethod
    @unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
    def setUpClass(cls):
        start_node(node_type="s2600kp")

    @classmethod
    @unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
    def tearDownClass(cls):
        stop_node()

    def test_qemu_local_fru(self):
        verify_qemu_local_fru(expect="BQKP41700055")

    def test_qemu_local_lan(self):
        verify_qemu_local_lan(expect="Auth Type")

    def test_qemu_local_sensor(self):
        verify_qemu_local_sensor(expect="P1 DTS Therm Mgn")

    def test_qemu_local_sdr(self):
        verify_qemu_local_sdr(expect="P1 DTS Therm Mgn")

    def test_qemu_local_sel(self):
        verify_qemu_local_sel(expect="Log area reset/cleared")

    def test_qemu_local_user(self):
        verify_qemu_local_user(expect="ADMINISTRATOR")

    def test_smbios_data(self):
        verify_smbios_data(expect_mfg="Manufacturer: EMC",
                           expect_product_name="Product Name: S2600KP")


@unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
class test_s2600tp(unittest.TestCase):

    @classmethod
    @unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
    def setUpClass(cls):
        start_node(node_type="s2600tp")

    @classmethod
    @unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
    def tearDownClass(cls):
        stop_node()

    def test_qemu_local_fru(self):
        verify_qemu_local_fru(expect="BQTP50400232")

    def test_qemu_local_lan(self):
        verify_qemu_local_lan(expect="Auth Type")

    def test_qemu_local_sensor(self):
        verify_qemu_local_sensor(expect="LSI3008 Temp")

    def test_qemu_local_sdr(self):
        verify_qemu_local_sdr(expect="LSI3008 Temp")

    def test_qemu_local_sel(self):
        verify_qemu_local_sel(expect="Log area reset/cleared")

    def test_qemu_local_user(self):
        verify_qemu_local_user(expect="ADMINISTRATOR")

    def test_smbios_data(self):
        verify_smbios_data(expect_mfg="Manufacturer: EMC",
                           expect_product_name="Product Name: S2600TP")


@unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
class test_s2600wtt(unittest.TestCase):

    @classmethod
    @unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
    def setUpClass(cls):
        start_node(node_type="s2600wtt")

    @classmethod
    @unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
    def tearDownClass(cls):
        stop_node()

    def test_qemu_local_fru(self):
        verify_qemu_local_fru(expect="BQWL50151054")

    def test_qemu_local_lan(self):
        verify_qemu_local_lan(expect="Auth Type")

    def test_qemu_local_sensor(self):
        verify_qemu_local_sensor(expect="FP NMI Diag Int")

    def test_qemu_local_sdr(self):
        verify_qemu_local_sdr(expect="FP NMI Diag Int")

    def test_qemu_local_sel(self):
        verify_qemu_local_sel(expect="Log area reset/cleared")

    def test_qemu_local_user(self):
        verify_qemu_local_user(expect="ADMINISTRATOR")

    def test_smbios_data(self):
        verify_smbios_data(expect_mfg="Manufacturer: EMC",
                           expect_product_name="Product Name: S2600WTT")


@unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
class test_dell_c6320(unittest.TestCase):

    @classmethod
    @unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
    def setUpClass(cls):
        start_node(node_type="dell_c6320")

    @classmethod
    @unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
    def tearDownClass(cls):
        stop_node()

    def test_qemu_local_fru(self):
        verify_qemu_local_fru(expect="CN7475157G0541")

    def test_qemu_local_lan(self):
        verify_qemu_local_lan(expect="Auth Type")

    def test_qemu_local_sensor(self):
        verify_qemu_local_sensor(expect="1.1V PG")

    def test_qemu_local_sdr(self):
        verify_qemu_local_sdr(expect="1.1V PG")

    def test_qemu_local_sel(self):
        verify_qemu_local_sel(expect="Log area reset/cleared")

    def test_qemu_local_user(self):
        verify_qemu_local_user(expect="ADMINISTRATOR")

    def test_smbios_data(self):
        verify_smbios_data(expect_mfg="Manufacturer: Dell Inc",
                           expect_product_name="Product Name: PowerEdge C6320")


@unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
class test_dell_r630(unittest.TestCase):

    @classmethod
    @unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
    def setUpClass(cls):
        start_node(node_type="dell_r630")

    @classmethod
    @unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
    def tearDownClass(cls):
        stop_node()

    def test_qemu_local_fru(self):
        verify_qemu_local_fru(expect="CN7475157N0560")

    def test_qemu_local_lan(self):
        verify_qemu_local_lan(expect="Auth Type")

    def test_qemu_local_sensor(self):
        verify_qemu_local_sensor(expect="NonFatalSSDError")

    def test_qemu_local_sdr(self):
        verify_qemu_local_sdr(expect="NonFatalSSDError")

    def test_qemu_local_sel(self):
        verify_qemu_local_sel(expect="Log area reset/cleared")

    def test_qemu_local_user(self):
        verify_qemu_local_user(expect="ADMINISTRATOR")

    def test_smbios_data(self):
        print("\033[93mDell R630 Manufacturer and Product Name is not ready yet.\033[0m")
        # verify_smbios_data(expect_mfg="Manufacturer: Dell Inc",
        #                    expect_product_name="Product Name: PowerEdge R630")


@unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
class test_dell_r730(unittest.TestCase):

    @classmethod
    @unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
    def setUpClass(cls):
        start_node(node_type="dell_r730")

    @classmethod
    @unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
    def tearDownClass(cls):
        stop_node()

    def test_qemu_local_fru(self):
        verify_qemu_local_fru(expect="CN7792163H023V")

    def test_qemu_local_lan(self):
        verify_qemu_local_lan(expect="Auth Type")

    def test_qemu_local_sensor(self):
        verify_qemu_local_sensor(expect="Fan1  ")

    def test_qemu_local_sdr(self):
        verify_qemu_local_sdr(expect="Fan1  ")

    def test_qemu_local_sel(self):
        verify_qemu_local_sel(expect="Log area reset/cleared")

    def test_qemu_local_user(self):
        verify_qemu_local_user(expect="ADMINISTRATOR")

    def test_smbios_data(self):
        verify_smbios_data(expect_mfg="Manufacturer: Dell Inc.",
                           expect_product_name="Product Name: PowerEdge R730")


class test_dell_r730xd(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        start_node(node_type="dell_r730xd")

    @classmethod
    def tearDownClass(cls):
        stop_node()

    def test_qemu_local_fru(self):
        verify_qemu_local_fru(expect="CN779215A5018M")

    def test_qemu_local_lan(self):
        verify_qemu_local_lan(expect="Auth Type")

    def test_qemu_local_sensor(self):
        verify_qemu_local_sensor(expect="Fan1 RPM")

    def test_qemu_local_sdr(self):
        verify_qemu_local_sdr(expect="Fan1 RPM")

    def test_qemu_local_sel(self):
        verify_qemu_local_sel(expect="Log area reset/cleared")

    def test_qemu_local_user(self):
        verify_qemu_local_user(expect="ADMINISTRATOR")

    def test_smbios_data(self):
        verify_smbios_data(expect_mfg="Manufacturer:",
                           expect_product_name="Product Name: R730 Base")
