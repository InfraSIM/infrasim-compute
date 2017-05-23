import unittest
import os
import time
import subprocess
import yaml
from test import fixtures
import re
from infrasim import model
from infrasim import InfraSimError
import paramiko
from infrasim.package_install import install_bintray_packages
import urllib

old_path = os.environ.get("PATH")
new_path = "{}/bin:{}".format(os.environ.get("PYTHONPATH"), old_path)
source_esxi_path = "ftp://10.62.59.23/idic/iso/esxi_img/esxi6p3-1.qcow2"
esxi_path = "/tmp/esxi6p3-1.qcow2"
tmp_conf_file = "/tmp/test.yml"
conf = {}


def run_command(cmd="", shell=True, stdout=None, stderr=None, interactive_input=""):
    child = subprocess.Popen(cmd, shell=shell,
                             stdout=stdout, stderr=stderr)
    cmd_result = child.communicate(interactive_input)
    cmd_return_code = child.returncode
    if cmd_return_code != 0:
        return -1, cmd_result[1]
    return 0, cmd_result[0]

def read_buffer(channel):
    while not channel.recv_ready():
        continue
    str_output = ''
    str_read = ''
    while True:
        str_read = str(channel.recv(40960))
        str_output += str_read
        prompts = re.findall(r'root@localhost:~', str_output)
        if len(prompts) == 2:
            break
        time.sleep(1)
    return str_output

def start_node():
    global conf
    fake_config = fixtures.FakeConfig()
    conf = fake_config.get_node_info()

    conf["compute"]["storage_backend"] = [
        {"type": "ahci",
         "max_drive_per_controller": 6,
         "drives": [{"bootindex":1, "size": 8, "file": esxi_path}]},
        {"type": "lsisas3008",
         "max_drive_per_controller": 6,
         "drives": [{"size": 8, "file": "/tmp/sda.img"}]}
    ]
    conf["compute"]["memory"]["size"] = 4096
    conf["compute"]["cpu"]["features"] = "+vmx"
    conf["compute"]["networks"][0]["device"] = "e1000"
    conf["compute"]["networks"][0]["network_mode"] = "nat"

    with open(tmp_conf_file, "w") as yaml_file:
        yaml.dump(conf, yaml_file, default_flow_style=False)

    result = run_command("qemu-img", True, subprocess.PIPE, subprocess.PIPE)[1]
    if "qemu-img: error while loading shared libraries: libaio.so.1" in result:
        try:
            run_command("apt-get install libaio.dev", True, subprocess.PIPE, subprocess.PIPE, "Y\n")
            print "installing libaio.dev"
        except Exception, e:
            raise e

    node = model.CNode(conf)
    node.init()
    node.precheck()
    node.start()

    time.sleep(10)
    import telnetlib
    tn = telnetlib.Telnet(host="127.0.0.1", port=2345)
    tn.read_until("(qemu)")
    tn.write("hostfwd_add ::2222-:22\n")
    tn.read_until("(qemu)")
    tn.close()

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    paramiko.util.log_to_file("filename.log")
    while True:
        try:
            ssh.connect("127.0.0.1", port=2222, username="root",
                        password="Passw0rd!", timeout=120)
            ssh.close()
            break
        except paramiko.SSHException:
            time.sleep(20)
            continue
        except paramiko.ssh_exception.NoValidConnectionsError:
            time.sleep(20)
            continue
        except Exception, e:
            raise e

def stop_node():
    global conf
    global tmp_conf_file

    node = model.CNode(conf)
    node.init()
    node.stop()
    node.terminate_workspace()
    conf = {}
    if os.path.exists(tmp_conf_file):
        os.unlink(tmp_conf_file)

    if os.path.exists(esxi_path):
        os.unlink(esxi_path)
    time.sleep(5)

def setup_module():
    os.environ["PATH"] = new_path

    nested_paths = ["/sys/module/kvm_intel/parameters", "/sys/module/kvm_adm/parameters"]
    param_ok_f = True
    nested_path = filter(lambda x: os.path.exists(x), nested_paths)
    if len(nested_path) == 1:
        is_nested = run_command('cat '+nested_path[0]+'/nested', True, subprocess.PIPE, subprocess.PIPE)[1]
        if "1" not in is_nested and "Y" not in is_nested:
            param_ok_f = False
    elif len(nested_path) == 0:
        param_ok_f = False
    ignore_msrs_path = "/sys/module/kvm/parameters"
    if os.path.exists(ignore_msrs_path):
        result = run_command('cat '+ignore_msrs_path+'/ignore_msrs', True, subprocess.PIPE, subprocess.PIPE)[1]
        if "1" not in result and "Y" not in result:
            param_ok_f = False
    else:
        param_ok_f = False
    if param_ok_f is False:
        raise Exception("Please enable nested virtualization in your kvm-based system.")

    try:
        urllib.urlretrieve(source_esxi_path, esxi_path)
    except:
        raise unittest.SkipTest("Need esxi image to test on esxi host.")
    install_bintray_packages("deb", "Qemu_Dev")

def teardown_module():
    global conf
    if conf:
        stop_node()
    os.environ["PATH"] = old_path
    install_bintray_packages("deb", "Qemu")


class test_esxi_cli(unittest.TestCase):
    ssh = paramiko.SSHClient()
    channel = None

    @classmethod
    def setUpClass(cls):
        start_node()

    @classmethod
    def tearDownClass(cls):
        stop_node()

    def test_esxi_ipmi_fru_list(self):
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect('127.0.0.1', port=2222, username='root',
                         password='Passw0rd!', timeout=10)
        self.channel = self.ssh.invoke_shell()

        self.channel.send("esxcli hardware ipmi fru list"+chr(13))
        time.sleep(1)
        str_output = read_buffer(self.channel)
        assert "Part Name: PowerEdge R730" in str_output

    def test_esxi_storage_device_list(self):
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect('127.0.0.1', port=2222, username='root',
                         password='Passw0rd!', timeout=10)
        self.channel = self.ssh.invoke_shell()

        self.channel.send("esxcli storage core device list"+chr(13))
        time.sleep(1)
        str_output = read_buffer(self.channel)
        assert "Display Name: QEMU Serial Attached SCSI Disk" in str_output
        assert "Display Name: Local ATA Disk" in str_output

    def test_esxi_storage_adpter_list(self):
        # place holder
        # lsisas3008 doesn't show in adapter list. It should be a bug in QEMU?
        pass
