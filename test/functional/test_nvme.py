"""
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
"""
import unittest
import os
import time
import re
import tempfile
from infrasim import model
from infrasim import helper
from infrasim import sshclient
from test import fixtures

old_path = os.environ.get('PATH')
new_path = '{}/bin:{}'.format(os.environ.get('PYTHONPATH'), old_path)
conf = {}


def setup_module():
    os.environ['PATH'] = new_path


def teardown_module():
    os.environ['PATH'] = old_path

@unittest.skipIf(not os.path.exists(fixtures.image),
                "Skip this test! No ubuntu image found in folder '/home/infrasim/jenkins/data'.\
Please build Qemu Ubuntu image follow guidance 'https://github.com/InfraSIM/tools/tree/master/packer'!")
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
        time.sleep(10)
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
    def setUpClass(cls):
        cls.start_node()

    @classmethod
    def tearDownClass(cls):
        if conf:
            cls.stop_node()

    def get_nvme_disks(self):
        # Return nvme , eg. ['/dev/nvme0n1', '/dev/nvme0n2']
        ssh = sshclient.SSH("127.0.0.1", "root", "root", port=2222)
        assert ssh.wait_for_host_up() is True
        nvme_list = []
        status, output = ssh.exec_command("nvme list |grep \"/dev\" |awk '{print $1}'")
        nvme_list = [dev.strip(os.linesep) for dev in output.strip().split()]
        return nvme_list

    def get_nvme_dev(self):
        # Return nvme drive device, eg. ['nvme0', 'nvme1']
        ssh = sshclient.SSH("127.0.0.1", "root", "root", port=2222)
        assert ssh.wait_for_host_up() is True
        nvme_dev_list = []
        status, output = ssh.exec_command("ls /sys/class/nvme")
        nvme_dev_list = output.split()
        return nvme_dev_list

    def get_nvme_ns_list(self, nvme):
        # Return name space id list, eg. ['1', '2']
        ssh = sshclient.SSH("127.0.0.1", "root", "root", port=2222)
        assert ssh.wait_for_host_up() is True
        status, output = ssh.exec_command("ls /sys/class/nvme/{} |grep {}".format(nvme, nvme))
        nsid_list = []

        for ns in output.split():
            id = re.search(r"nvme(\d+)n(\d+)", ns)
            nsid = id.group(2)
            nsid_list.append(nsid)
        return nsid_list

    def test_nvme_disk_count(self):
        global conf
        nvme_list = self.get_nvme_disks()
        nvme_config_list = []
        for drive in conf["compute"]["storage_backend"]:
            if drive["type"] == "nvme":
                nvme_config_list.append(drive["namespaces"])
        assert len(nvme_list) == sum(nvme_config_list)

    def _create_gen_bin_script(self, bin_file_name, pattern, block=4):
        # Parameters:
        # script_name, eg. "/tmp/script_name.py"
        # pattern, eg. "0xff"
        # Return script path
        ssh = sshclient.SSH("127.0.0.1", "root", "root", port=2222)
        assert ssh.wait_for_host_up() is True
        script_name = "/tmp/gen_{}.py".format(str(pattern))
        script_content = '''#!/usr/bin/env python
import struct
with open('{}', 'wb') as f:
    for i in range(512 * {}):
        f.write(struct.pack('=B',{}))
'''.format(bin_file_name, block, pattern)
        status, output = ssh.exec_command("echo \"{}\" > {}".format(script_content, script_name))
        return script_name

    def _run_gen_bin_script(self, bin_file_name, script_name):
        ssh = sshclient.SSH("127.0.0.1", "root", "root", port=2222)
        assert ssh.wait_for_host_up() is True
        status, output = ssh.exec_command("python {}".format(script_name))
        return status

    def _clean_up(self):
        # Clean up temperary files
        ssh = sshclient.SSH("127.0.0.1", "root", "root", port=2222)
        assert ssh.wait_for_host_up() is True
        status, output = ssh.exec_command("ls /tmp/")
        print "OUTPUT: {}".format(output)
        status, output = ssh.exec_command("rm /tmp/*")
        print "STATUS: {}".format(status)
        return status

    def test_read_write_verify(self):
        ssh = sshclient.SSH("127.0.0.1", "root", "root", port=2222)
        assert ssh.wait_for_host_up() is True

        pattern = 0xff
        bin_file_name = tempfile.mktemp(suffix=".bin", prefix="nvme-test-")
        script_name = self._create_gen_bin_script(bin_file_name, pattern)
        assert self._run_gen_bin_script(bin_file_name, script_name) == 0

        nvme_list = self.get_nvme_disks()
        for dev in nvme_list:
            # Write 0xff to 2048 byte of nvme disks
            status, output = ssh.exec_command("nvme write {} -d {} -c 4 -z 2048".format(dev, bin_file_name))
            assert status == 0

            # Verify data consistent as written
            read_data_file = "/tmp/read_data"
            status, output = ssh.exec_command("nvme read {} -c 4 -z 2048 -d {}".format(dev, read_data_file))
            assert status == 0
            status, _ = ssh.exec_command("cmp {} {}".format(bin_file_name, read_data_file))
            assert status == 0

        pattern = 0x00
        bin_file_name = tempfile.mktemp(suffix=".bin", prefix="nvme-test-")
        script_name = self._create_gen_bin_script(bin_file_name, pattern)
        assert self._run_gen_bin_script(bin_file_name, script_name) == 0

        for dev in nvme_list:
            # restore drive data to all zero
            status, _ = ssh.exec_command("nvme write {} -d {} -c 4 -z 2048".format(dev, bin_file_name))
            assert status == 0
            read_data_file = "/tmp/read_data"
            status, _ = ssh.exec_command("nvme read {} -c 4 -z 2048 -d {}".format(dev, read_data_file))
            assert status == 0
            status, _ = ssh.exec_command("cmp {} {}".format(bin_file_name, read_data_file))
            assert status == 0
        self._clean_up()

    def test_id_ctrl(self):
        global conf
        nvme_list = self.get_nvme_disks()
        ssh = sshclient.SSH("127.0.0.1", "root", "root", port=2222)
        assert ssh.wait_for_host_up() is True
        nvme_config_list = []
        nvme_id_ctrl_list = []

        # initialize nvme id-ctrl list
        for dev in nvme_list:
            status, ctrl_data = ssh.exec_command("nvme id-ctrl {}".format(dev))

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

        ssh = sshclient.SSH("127.0.0.1", "root", "root", port=2222)
        assert ssh.wait_for_host_up() is True
        for dev in nvme_list:
            status, rsp = ssh.exec_command("nvme get-ns-id {}".format(dev))
            ns_id_get = rsp.split(":")[2]
            result = re.search(r"nvme(\d+)n(\d+)", dev)
            ns_id_read = result.group(2)
            assert int(ns_id_get) == int(ns_id_read)

    def test_get_log(self):
        global conf
        nvme_dev_list = self.get_nvme_dev()
        ssh = sshclient.SSH("127.0.0.1", "root", "root", port=2222)
        assert ssh.wait_for_host_up() is True
        # Now infrasim design only support log_id(1, 2, 3)
        log_id_max = 3
        for nvme in nvme_dev_list:
            nsid_list = self.get_nvme_ns_list(nvme)
            for ns_id in nsid_list:
                for log_id in range(1, log_id_max + 1):
                    status, rsp = ssh.exec_command(
                        "nvme get-log /dev/{} -n {} -i {} -l 512".format(nvme, ns_id, log_id))
                    print rsp
                    assert nvme, ns_id in rsp
                    assert str(log_id) in rsp

    def test_smart_log(self):
        # To get MT devices list.
        nvme_model_list = []
        ssh = sshclient.SSH("127.0.0.1", "root", "root", port=2222)
        assert ssh.wait_for_host_up() is True
        status, output = ssh.exec_command("nvme list |grep \"/dev\" |awk '{print $1,$3}'")
        nvme_model_list = output.split("\n")[:-1]
        mt_list = []
        for item in nvme_model_list:
            if str(item.split(" ")[1]) == "MTC_8GB":
                mt_list.append(item.split(" ")[0].split("/")[2])

        nvme_dev_list = self.get_nvme_dev()
        for nvme in nvme_dev_list:
            nsid_list = self.get_nvme_ns_list(nvme)
            for ns_id in nsid_list:
                status, output = ssh.exec_command("nvme smart-log /dev/{} -n {}".format(nvme, ns_id))
                print output
                # FIXME: Once IN-1393 fixed, change critical_warnings to "0" to reflect NVMe drive is healthy.
                assert re.search(r"critical_warning\s+:\s+(0x\d|\d+)", output)
                assert re.search(r"temperature\s+:\s+(\d+)(\s+)C", output)
                assert re.search(r"available_spare\s+:\s+(\d+)%", output)
                assert re.search(r"available_spare_threshold\s+:\s+(\d+)%", output)

                # FIXME: For MT, there are two Temperature Sensors need to check, now this step is expected to FAIL.
                '''
                if "{}n{}".format(nvme, ns_id) in mt_list:
                    print "This is MT, need to check two temperature sensors"
                    assert re.search(r"Temperature(\s+)Sensor(\s+)(\d+)(\s+):(\s+)(\d+)(\s+)C", rsp)
                '''

    def test_error_log(self):
        nvme_disk_list = self.get_nvme_disks()
        ssh = sshclient.SSH("127.0.0.1", "root", "root", port=2222)
        assert ssh.wait_for_host_up() is True
        for nvme in nvme_disk_list:
            status, output = ssh.exec_command("nvme error-log {}".format(nvme))
            assert re.search("Error Log Entries for device:{} entries:(\d+)".format(nvme.split("/")[2]), output)

    def test_write_zeroes(self):
        nvme_list = self.get_nvme_disks()
        ssh = sshclient.SSH("127.0.0.1", "root", "root", port=2222)
        assert ssh.wait_for_host_up() is True

        pattern = 0xff
        bin_file_name = tempfile.mktemp(suffix=".bin", prefix="nvme-test-")
        script_name = self._create_gen_bin_script(bin_file_name, pattern)
        assert self._run_gen_bin_script(bin_file_name, script_name) == 0

        for dev in nvme_list:
            # Write 0xff to 2048 byte of nvme disks
            status, output = ssh.exec_command("nvme write {} -d {} -c 4 -z 2048".format(dev, bin_file_name))
            assert status == 0
            read_data_file = "/tmp/read_data.bin"

            # Verify data consistent as written
            status, _ = ssh.exec_command("nvme read {} -c 4 -z 2048 -d {}".format(dev, read_data_file))
            assert status == 0

            status, _ = ssh.exec_command("cmp {} {}".format(bin_file_name, read_data_file))
            assert status == 0

        # Restore drive data to all zero
        pattern = 0x00
        bin_file_name = tempfile.mktemp(suffix=".bin", prefix="nvme-test-")
        script_name = self._create_gen_bin_script(bin_file_name, pattern)
        assert self._run_gen_bin_script(bin_file_name, script_name) == 0
        for dev in nvme_list:
            # Write 0x00 to 2048 byte of nvme disks
            status, output = ssh.exec_command("nvme write-zeroes {} -c 4".format(dev))
            assert status == 0

            read_data_file = "/tmp/read_zero.bin"
            status, _ = ssh.exec_command("nvme read {} -c 4 -z 2048 -d {}".format(dev, read_data_file))
            status, _ = ssh.exec_command("cmp {} {}".format(bin_file_name, read_data_file))
            assert status == 0
        self._clean_up()

    def test_identify_namespace(self):
        nvme_list = self.get_nvme_disks()
        ssh = sshclient.SSH("127.0.0.1", "root", "root", port=2222)
        assert ssh.wait_for_host_up() is True
        for dev in nvme_list:
            status, rsp_id_ns = ssh.exec_command("nvme id-ns {}".format(dev))
            # Check identity keywords existance in command output
            key_words = ["nsze", "ncap", "nuse", "nsfeat", "nlbaf", "flbas", "mc",
                         "dpc", "dps", "nmic", "rescap", "fpi", "nawun", "nawupf",
                         "nacwu", "nabsn", "nabo", "nabspf", "noiob", "nvmcap",
                         "nguid", "eui64", "lbaf"]
            print rsp_id_ns
            current_lba_index = None
            for line in rsp_id_ns.split(os.linesep):
                if line.startswith('NVME'):
                    continue

                if line.startswith('lbaf'):
                    robj = re.search(
                        r'lbaf\s+(?P<index>\d+)\s+:\s+ms:(?P<ms>\d+)\s+(lba)?ds:'
                        r'(?P<ds>\d+)\s+rp:\d+(\s+)?(?P<used>\(.*\))?',
                        line)
                    assert robj
                    assert int(robj.groupdict().get('index')) < 5
                    if robj.groupdict().get('used'):
                        current_lba_index = int(robj.groupdict().get('index'))
                        assert current_lba_index is not None
                else:
                    robj = re.search(r'(?P<key>\w+)\s+:\s+.*', rsp_id_ns)
                    assert robj
                    assert robj.groupdict().get('key') in key_words

            # Check namespace logical block size in command output
            status, rsp_sg = ssh.exec_command("sg_readcap {}".format(dev))
            rsp_sg = re.search(r"blocks=(\d+)", rsp_sg)
            sg_block_size = hex(int(rsp_sg.group(1)))

            nsze = re.search(r"nsze\s*:\s*(0x\d+)", rsp_id_ns).group(1)
            assert sg_block_size == nsze

    def test_get_set_arb_feature(self):
        # Test get and set arbitration feature.
        nvme_list = self.get_nvme_disks()
        ssh = sshclient.SSH("127.0.0.1", "root", "root", port=2222)
        assert ssh.wait_for_host_up() is True
        # select [0-3]: current/default/saved/supported
        sel = 0
        # feature id 1: arbitration
        feature_id = 1
        for dev in nvme_list:
            status, rsp_before_set = ssh.exec_command("nvme get-feature {} -f {} -s {}".format(dev, feature_id, sel))
            print "Before set: ", rsp_before_set
            match_obj = re.search(
                r'^get-feature:0x(?P<feature_id>\d+) \(Arbitration\), Current value:\s?0x(?P<value>[0-9a-fA-F]+)',
                rsp_before_set)
            assert match_obj
            assert feature_id == int(match_obj.groupdict().get('feature_id'), 16)

            # Prepare set feature value
            exp_arb_after_set = int(match_obj.groupdict().get('value'), 16) + 1

            # Set feature
            status, rsp_set = ssh.exec_command(
                "nvme set-feature {} -f {} -v {}".format(dev, feature_id, exp_arb_after_set))
            assert status == 0

            # Get feature again and verify
            status, rsp_after_set = ssh.exec_command("nvme get-feature {} -f {} -s {}".format(dev, feature_id, sel))
            print "After set: ", rsp_after_set
            assert status == 0
            match_obj = re.search(r"Current value:\s?0x([0-9a-fA-F]+)", rsp_after_set)
            assert match_obj
            arb_after_set = int(match_obj.group(1), 16)
            assert exp_arb_after_set == arb_after_set

    def test_get_set_temp_feature(self):
        # Test get and set temparature feature.
        nvme_list = self.get_nvme_disks()
        ssh = sshclient.SSH("127.0.0.1", "root", "root", port=2222)
        assert ssh.wait_for_host_up() is True
        # select [0-3]: current/default/saved/supported
        sel = 0
        # feature id 4: temparature
        feature_id = 4
        for dev in nvme_list:
            status, rsp_before_set = ssh.exec_command("nvme get-feature {} -f {} -s {}".format(dev, feature_id, sel))
            print rsp_before_set
            match_obj = re.search(
                r'^get-feature:0x(?P<id>\d+) \(Temperature Threshold\), Current value:\s?0x(?P<value>[0-9a-fA-F]+)',
                rsp_before_set)
            assert match_obj
            assert feature_id == int(match_obj.groupdict().get('id'), 16)
            # Check keywords existance in command output

            # Prepare set temparature feature value
            exp_temp_after_set = int(match_obj.groupdict().get('value'), 16) + 1

            # Set feature
            status, rsp_set = ssh.exec_command(
                "nvme set-feature {} -f {} -v {}".format(dev, feature_id, exp_temp_after_set))

            # Get feature again and verify
            status, rsp_after_set = ssh.exec_command("nvme get-feature {} -f {} -s {}".format(dev, feature_id, sel))
            temp_after_set = re.search(r"Current value:\s?0x([0-9a-fA-F]+)", rsp_after_set).group(1)
            assert exp_temp_after_set == int(temp_after_set, 16)

    def test_flush(self):
        # Test flush command, it commit data/metadata associated with the specified namespace to volatile media.
        nvme_ctrls = self.get_nvme_dev()
        ssh = sshclient.SSH("127.0.0.1", "root", "root", port=2222)
        assert ssh.wait_for_host_up() is True
        for nvme in nvme_ctrls:
            ns_list = self.get_nvme_ns_list(nvme)
            for ns in ns_list:
                status, output = ssh.exec_command("nvme flush /dev/{}n{} -n {}".format(nvme, ns, ns))
                assert status == 0
                print output

                # Check keywords existance in command output
                key_words = ["Flush:", "NVMe", "success"]
                assert set(key_words) <= set(output.split())

    def test_compare(self):
        # Test compare command, compare success when disk data of specified range is identical
        # with the specified data file.
        nvme_list = self.get_nvme_disks()

        start_block = 0
        data_size = 4096
        block_count = 8
        ssh = sshclient.SSH("127.0.0.1", "root", "root", port=2222)
        assert ssh.wait_for_host_up() is True

        pattern = 0xff
        bin_file_name = tempfile.mktemp(suffix=".bin", prefix="nvme-test-")
        script_name = self._create_gen_bin_script(bin_file_name, pattern, block_count)
        assert self._run_gen_bin_script(bin_file_name, script_name) == 0
        for dev in nvme_list:
            status, output = ssh.exec_command(
                "nvme compare {} -z {} -s {} -c {} -d {}\n".format(dev, data_size, start_block,
                                                                   block_count, bin_file_name))
            assert 0 != status
            print "compare OUTPUT: {}".format(output)
            cobj = re.search(r"[Cc]ompare:\s?COMPARE_FAILED\(\d+\)", output)
            assert cobj
            # assert "COMPARE_FAILED" in output

            status, output = ssh.exec_command(
                "nvme write {} -z {} -s {} -c {} -d {}\n".format(dev, data_size, start_block,
                                                                 block_count, bin_file_name))
            assert 0 == status
            print "write OUTPUT: {}".format(output)
            cobj = re.search(r"[Ww]rite:\s?[Ss]uccess", output)
            assert cobj

            status, output = ssh.exec_command(
                "nvme compare {} -z {} -s {} -c {} -d {}\n".format(dev, data_size, start_block,
                                                                   block_count, bin_file_name))
            assert 0 == status
            print "compare OUTPUT: {}".format(output)
            cobj = re.search(r"[Cc]ompare:\s?[Ss]uccess", output)
            assert cobj
