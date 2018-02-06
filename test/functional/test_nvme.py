"""
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
"""
import unittest
import os
import time
import re
from infrasim import model
from infrasim import helper
from test import fixtures

old_path = os.environ.get('PATH')
new_path = '{}/bin:{}'.format(os.environ.get('PYTHONPATH'), old_path)
image = "/home/infrasim/jenkins/ubuntu14.04.4.qcow2"

conf = {}

def setup_module():
    os.environ['PATH'] = new_path


def teardown_module():
    os.environ['PATH'] = old_path


class test_nvme(unittest.TestCase):

    @staticmethod
    def start_node():
        global conf
        nvme_config = fixtures.NvmeConfig()
        conf = nvme_config.get_node_info()
        node = model.CNode(conf)
        node.init()
        node.precheck()
        node.start()
        time.sleep(3)
        helper.port_forward(node)

    @staticmethod
    def stop_node():
        global conf
        node = model.CNode(conf)
        node.init()
        node.stop()
        node.terminate_workspace()
        conf = {}

        time.sleep(5)

    @classmethod
    @unittest.skipIf(not os.path.exists(image), "There is no ubuntu image, skip this test")
    def setUpClass(cls):
        cls.start_node()

    @classmethod
    def tearDownClass(cls):
        if conf:
            cls.stop_node()

    def get_nvme_disks(self):
        ssh = helper.prepare_ssh()
        nvme_list = []
        stdin, stdout, stderr = ssh.exec_command("sudo nvme list |grep \"/dev\" |awk '{print $1}'")
        while not stdout.channel.exit_status_ready():
            pass
        nvme_list = stdout.channel.recv(2048).split()
        ssh.close()
        return nvme_list

    def get_nvme_dev(self):
        ssh = helper.prepare_ssh()
        nvme_dev_list = []
        stdin, stdout, stderr = ssh.exec_command("sudo ls /sys/class/nvme")
        while not stdout.channel.exit_status_ready():
            pass
        nvme_dev_list = stdout.channel.recv(2048).split()
        ssh.close()
        return nvme_dev_list

    def get_nvme_ns_list(self, nvme):
        ssh = helper.prepare_ssh()
        stdin, stdout, stderr = ssh.exec_command("ls /sys/class/nvme/{} |grep {}".format(nvme, nvme))
        response = stdout.channel.recv(2048)
        nsid_list = []

        for ns in response.split():
            id = re.search(r"nvme(\d+)n(\d+)", ns)
            nsid = id.group(2)
            nsid_list.append(nsid)

        return nsid_list

    def test_nvme_disk_count(self):
        global conf
        image = "/home/infrasim/jenkins/ubuntu14.04.4.qcow2"
        if not os.path.exists(image):
            self.skipTest("There is no ubuntu image, skip this test")

        nvme_list = self.get_nvme_disks()
        nvme_config_list = []
        for drive in conf["compute"]["storage_backend"]:
            if drive["type"] == "nvme":
                nvme_config_list.append(drive["namespaces"])
        assert len(nvme_list) == sum(nvme_config_list)

    def test_read_write_verify(self):
        nvme_list = self.get_nvme_disks()
        ssh = helper.prepare_ssh()
        for dev in nvme_list:
            # Write 0xff to 2048 byte of nvme disks
            stdin, stdout, stderr = ssh.exec_command("nvme write {} -d ff_binfile -c 4 -z 2048".format(dev))
            while not stdout.channel.exit_status_ready():
                pass

            # Verify data consistent as written
            stdin, stdout, stderr = ssh.exec_command("nvme read {} -c 4 -z 2048 >read_data".format(dev))
            while not stdout.channel.exit_status_ready():
                pass

            stdin, stdout, stderr = ssh.exec_command("hexdump read_data -n 2048".format(dev))
            while not stdout.channel.exit_status_ready():
                pass
            read_data = stdout.channel.recv(2048)

            stdin, stdout, stderr = ssh.exec_command("hexdump ff_binfile -n 2048".format(dev))
            while not stdout.channel.exit_status_ready():
                pass
            binfile_data = stdout.channel.recv(2048)
            assert read_data == binfile_data

            # restore drive data to all zero
            stdin, stdout, stderr = ssh.exec_command("nvme write {} -d 0_binfile -c 4 -z 2048".format(dev))
            while not stdout.channel.exit_status_ready():
                pass

            stdin, stdout, stderr = ssh.exec_command("nvme read {} -c 4 -z 2048 >read_data".format(dev))
            while not stdout.channel.exit_status_ready():
                pass

            stdin, stdout, stderr = ssh.exec_command("hexdump read_data -n 2048".format(dev))
            while not stdout.channel.exit_status_ready():
                pass
            read_data = stdout.channel.recv(2048)

            stdin, stdout, stderr = ssh.exec_command("hexdump 0_binfile".format(dev))
            while not stdout.channel.exit_status_ready():
                pass
            binfile_data = stdout.channel.recv(2048)
            assert read_data == binfile_data
        ssh.close()

    def test_id_ctrl(self):
        global conf
        nvme_list = self.get_nvme_disks()
        ssh = helper.prepare_ssh()
        nvme_config_list = []
        nvme_id_ctrl_list = []

        # initialize nvme id-ctrl list
        for dev in nvme_list:
            stdin, stdout, stderr = ssh.exec_command("nvme id-ctrl {}".format(dev))
            while not stdout.channel.exit_status_ready():
                pass
            ctrl_data = stdout.channel.recv(2048)

            li = ctrl_data.split("\n")
            id_ctrl = {}
            for i in li:
                pattern = r"\w+\s*:\s*\w+\s*"
                result = re.match(pattern, i)
                if result:
                    elem = result.group(0)
                    id_ctrl[elem.split(":")[0].strip()] = elem.split(":")[1].strip()
            if id_ctrl:
                nvme_id_ctrl_list.append(id_ctrl)
        ssh.close()

        # initialize nvme drive list from yml configure file
        for disk in conf["compute"]["storage_backend"]:
            if disk["type"] == "nvme":
                nvme_config_list.append(disk)

        # compare nvme info from id-ctrl list against yml configure file
        # currently we compares:
        # 1. disk size
        # 2. serial number
        match_list = []
        for id_ctrl in nvme_id_ctrl_list:
            for id_config in nvme_config_list:
                if id_ctrl["sn"] == id_config["serial"]:
                    match_list.append(id_config["serial"])
                    assert "MTC_{}GB".format(id_config["drives"][0]["size"]) == id_ctrl["mn"]
        assert len(match_list) == len(nvme_list)

    def test_get_ns_id(self):
        global conf
        nvme_list = self.get_nvme_disks()
        ssh = helper.prepare_ssh()

        for dev in nvme_list:
            stdin, stdout, stderr = ssh.exec_command("nvme get-ns-id {}".format(dev))
            while not stdout.channel.exit_status_ready():
                pass
            rsp = stdout.channel.recv(2048)
            ns_id_get = rsp.split(":")[2]
            result = re.search(r"nvme(\d+)n(\d+)", dev)
            ns_id_read = result.group(2)
            assert int(ns_id_get) == int(ns_id_read)
        ssh.close()


    def test_get_log(self):
        global conf
        nvme_dev_list = self.get_nvme_dev()
        ssh = helper.prepare_ssh()
        # Now infrasim design only support log_id(1, 2, 3)
        log_id_max = 3
        for nvme in nvme_dev_list:
            nsid_list = self.get_nvme_ns_list(nvme)
            for ns_id in nsid_list:
                for log_id in range(1, log_id_max + 1):
                    stdin, stdout, stderr = ssh.exec_command("nvme get-log /dev/{} -n {} -i {} -l 512".format(nvme, ns_id, log_id))
                    while not stdout.channel.exit_status_ready():
                        pass
                    rsp = stdout.channel.recv(2048)
                    print rsp
                    assert nvme, ns_id in rsp
                    assert str(log_id) in rsp
        ssh.close()

    def test_smart_log(self):
        # To get MT devices list.
        nvme_model_list = []
        ssh = helper.prepare_ssh()
        stdin, stdout, stderr = ssh.exec_command("sudo nvme list |grep \"/dev\" |awk '{print $1,$3}'")
        while not stdout.channel.exit_status_ready():
            pass
        nvme_model_list = stdout.channel.recv(2048).split("\n")[:-1]
        mt_list = []
        for item in nvme_model_list:
            if str(item.split(" ")[1]) == "MTC_8GB":
                mt_list.append(item.split(" ")[0].split("/")[2])
        ssh.close()

        nvme_dev_list = self.get_nvme_dev()
        ssh = helper.prepare_ssh()
        for nvme in nvme_dev_list:
            nsid_list = self.get_nvme_ns_list(nvme)
            for ns_id in nsid_list:
                stdin, stdout, stderr = ssh.exec_command("nvme smart-log /dev/{} -n {}".format(nvme, ns_id))
                while not stdout.channel.exit_status_ready():
                    pass
                rsp = stdout.channel.recv(2048)
                print rsp
                # FIXME: Once IN-1393 fixed, change critical_warnings to "0" to reflect NVMe drive is healthy.
                assert re.search(r"critical_warning(\s+):(\s+)0x(\d+)", rsp)
                assert re.search(r"temperature(\s+):(\s+)(\d+)(\s+)C", rsp)
                assert re.search(r"available_spare(\s+):(\s+)(\d+)%", rsp)
                assert re.search(r"available_spare_threshold(\s+):(\s+)(\d+)%", rsp)

                # FIXME: For MT, there are two Temperature Sensors need to check, now this step is expected to FAIL.
                '''
                if "{}n{}".format(nvme, ns_id) in mt_list:
                    print "This is MT, need to check two temperature sensors"
                    assert re.search(r"Temperature(\s+)Sensor(\s+)(\d+)(\s+):(\s+)(\d+)(\s+)C", rsp)
                '''
        ssh.close()

    def test_error_log(self):
        nvme_disk_list = self.get_nvme_disks()
        ssh = helper.prepare_ssh()
        for nvme in nvme_disk_list:
            stdin, stdout, stderr = ssh.exec_command("nvme error-log {}".format(nvme))
            while not stdout.channel.exit_status_ready():
                pass
            rsp = stdout.channel.recv(2048)
            assert re.search("Error Log Entries for device:{} entries:(\d+)".format(nvme.split("/")[2]), rsp)
        ssh.close()

    def test_write_zeroes(self):

        nvme_list = self.get_nvme_disks()
        ssh = helper.prepare_ssh()
        for dev in nvme_list:
            # Write 0xff to 2048 byte of nvme disks
            stdin, stdout, stderr = ssh.exec_command("nvme write {} -d ff_binfile -c 4 -z 2048".format(dev))
            while not stdout.channel.exit_status_ready():
                pass

            # Verify data consistent as written
            stdin, stdout, stderr = ssh.exec_command("nvme read {} -c 4 -z 2048 > read_data".format(dev))
            while not stdout.channel.exit_status_ready():
                pass

            stdin, stdout, stderr = ssh.exec_command("hexdump read_data -n 2048".format(dev))
            while not stdout.channel.exit_status_ready():
                pass
            read_data = stdout.channel.recv(2048)
            stdin, stdout, stderr = ssh.exec_command("hexdump ff_binfile".format(dev))
            while not stdout.channel.exit_status_ready():
                pass
            binfile_data = stdout.channel.recv(2048)
            assert read_data == binfile_data

            # restore drive data to all zero
            stdin, stdout, stderr = ssh.exec_command("nvme write-zeroes {} -c 4".format(dev))
            while not stdout.channel.exit_status_ready():
                pass

            stdin, stdout, stderr = ssh.exec_command("nvme read {} -c 4 -z 2048 > read_zero".format(dev))
            while not stdout.channel.exit_status_ready():
                pass

            stdin, stdout, stderr = ssh.exec_command("hexdump read_zero -n 2048".format(dev))
            while not stdout.channel.exit_status_ready():
                pass
            read_data = stdout.channel.recv(2048)

            stdin, stdout, stderr = ssh.exec_command("hexdump 0_binfile -n 2048".format(dev))
            while not stdout.channel.exit_status_ready():
                pass
            binfile_data = stdout.channel.recv(2048)
            assert read_data == binfile_data
        ssh.close()













