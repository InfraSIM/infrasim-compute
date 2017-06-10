"""
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
"""
import unittest
import os
import yaml
from infrasim import model
from infrasim import config
from infrasim import run_command
from test import fixtures
from infrasim.workspace import Workspace
from infrasim import InfraSimError
from infrasim import helper
import time
import paramiko
old_path = os.environ.get('PATH')
new_path = '{}/bin:{}'.format(os.environ.get('PYTHONPATH'), old_path)


def setup_module():
    os.environ['PATH'] = new_path


def teardown_module():
    os.environ['PATH'] = old_path


class test_kcs_io(unittest.TestCase):
    global tmp_conf_file
    global format_f
    global test_img_file
    global conf
    test_img_file = '/tmp/kcs.img'
    tmp_conf_file = '/tmp/test.yml'
    conf = {}
    format_f = False

    def start_node(self):
        global conf
        fake_config = fixtures.FakeConfig()
        conf = fake_config.get_node_info()
        conf['compute']['storage_backend'] = [{
            'type': 'ahci',
            'max_drive_per_controller': 6,
            'drives': [
                {'size': 8, 'file': test_img_file, 'boot_index': 1},
                {'size': 8, 'file': '/tmp/sdb.img'},
                {'size': 8, 'file': '/tmp/sdc.img'},
                {'size': 8, 'file': '/tmp/sdd.img'},
                {'size': 8, 'file': '/tmp/sde.img'},
                {'size': 8, 'file': '/tmp/sdf.img'}
            ]
        },
            {
            'type': 'ahci',
            'max_drive_per_controller': 6,
            'drives': [
                {'size': 8, 'file': '/tmp/sdg.img'},
                {'size': 8, 'file': '/tmp/sdh.img'},
                {'size': 8, 'file': '/tmp/sdi.img'},
                {'size': 8, 'file': '/tmp/sdj.img'},
                {'size': 8, 'file': '/tmp/sdk.img'},
                {'size': 8, 'file': '/tmp/sdl.img'}]
        }]

        with open(tmp_conf_file, 'w') as yaml_file:
            yaml.dump(conf, yaml_file, default_flow_style=False)
        os.system('infrasim config add test {}'.format(tmp_conf_file))
        node = model.CNode(conf)
        node.init()
        node.precheck()
        node.start()
        time.sleep(3)

    def stop_node(self):
        global conf
        node = model.CNode(conf)
        node.init()
        node.stop()
        node.terminate_workspace()
        conf = {}
        if os.path.exists(tmp_conf_file):
            os.unlink(tmp_conf_file)
        time.sleep(5)

    def port_forward(self):
        import telnetlib
        tn = telnetlib.Telnet(host='127.0.0.1', port=2345)
        tn.read_until('(qemu)')
        tn.write('hostfwd_add ::2222-:22\n')
        tn.read_until('(qemu)')
        tn.close()

    def prepare_ssh(self):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        paramiko.util.log_to_file('filename.log')
        helper.try_func(
            600,
            paramiko.SSHClient.connect,
            ssh,
            '127.0.0.1',
            port=2222,
            username='root',
            password='root',
            timeout=120)
        time.sleep(2)
        return ssh

    def setUp(cls):
        DOWNLOAD_URL = 'https://github.com/InfraSIM/test/raw/master/image/kcs.img'
        MD5_KCS_IMG = 'cfdf7d855d2f69c67c6e16cc9b53f0da'
        helper.fetch_image(DOWNLOAD_URL, MD5_KCS_IMG, test_img_file)

        cls.start_node()
        cls.port_forward()

    def tearDown(cls):
        if conf:
            cls.stop_node()

    def run_command(
            cmd='',
            shell=True,
            stdout=None,
            stderr=None,
            interactive_input=''):
        child = subprocess.Popen(
            cmd, shell=shell, stdout=stdout, stderr=stderr)
        cmd_result = child.communicate(interactive_input)
        cmd_return_code = child.returncode
        if cmd_return_code != 0:
            return (-1, cmd_result[1])
        return (0, cmd_result[0])

    def test_file_existance_after_node_restart(self):
        # Write disk
        node_name = conf['name']
        ssh = self.prepare_ssh()
        stdin, stdout, stderr = ssh.exec_command('touch /root/source.bin')
        while not stdout.channel.exit_status_ready():
            pass
        stdin, stdout, stderr = ssh.exec_command(
            "echo 'Test message is found! :D' >> /root/source.bin")
        while not stdout.channel.exit_status_ready():
            pass

        # FIXME: close ssh is walk around to issue of ssh connection go inactive
        # which seems like a paramiko issue? So as other ssh.close() in file.
        ssh.close()
        ssh = self.prepare_ssh()
        stdin, stdout, stderr = ssh.exec_command(
            'dd if=/root/source.bin of=/dev/sdb bs=512 seek=0 count=1 conv=fsync')
        while not stdout.channel.exit_status_ready():
            pass

        ssh.close()

        # Check disk content intact after node restart
        run_command("infrasim node restart {}".format(node_name))
        self.port_forward()
        ssh = self.prepare_ssh()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect("127.0.0.1", port=2222, username="root",
                    password="root", timeout=10)

        stdin, stdout, stderr = ssh.exec_command('touch /root/source.bin')
        while not stdout.channel.exit_status_ready():
            pass
        stdin, stdout, stderr = ssh.exec_command(
            "echo 'Test message is found! :D' >> /root/source.bin")
        while not stdout.channel.exit_status_ready():
            pass

        stdin, stdout, stderr = ssh.exec_command(
            'dd if=/dev/sdb of=/root/target.bin bs=512 skip=0 count=1 conv=fsync')
        while not stdout.channel.exit_status_ready():
            pass

        ssh.close()

        ssh = self.prepare_ssh()
        stdin, stdout, stderr = ssh.exec_command(
            'diff /root/source.bin /root/target.bin -B')
        while not stdout.channel.exit_status_ready():
            pass

        lines = stdout.channel.recv(2048)
        assert lines is ''
        ssh.close()

        ssh = self.prepare_ssh()
        stdin, stdout, stderr = ssh.exec_command('rm /root/target.bin')
        while not stdout.channel.exit_status_ready():
            pass

        stdin, stdout, stderr = ssh.exec_command('ls /root')
        while not stdout.channel.exit_status_ready():
            pass

        lines = stdout.channel.recv(2048)
        assert 'target.bin' not in lines
        stdin, stdout, stderr = ssh.exec_command('rm /root/source.bin')
        while not stdout.channel.exit_status_ready():
            pass

        stdin, stdout, stderr = ssh.exec_command('ls /root')
        while not stdout.channel.exit_status_ready():
            pass

        lines = stdout.channel.recv(2048)
        assert 'source.bin' not in lines

    def test_copy_file_across_drives(self):
        node_name = conf['name']
        ssh = self.prepare_ssh()
        stdin, stdout, stderr = ssh.exec_command('touch /root/source.bin')
        while not stdout.channel.exit_status_ready():
            pass

        stdin, stdout, stderr = ssh.exec_command(
            "echo 'Test message is found! :D' >> /root/source.bin")
        while not stdout.channel.exit_status_ready():
            pass

        for i in ('b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l'):
            stdin, stdout, stderr = ssh.exec_command(
                'dd if=/root/source.bin of=/dev/sd' + i + ' bs=512 seek=0 count=1 conv=fsync')
            while not stdout.channel.exit_status_ready():
                pass

        for i in ('b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l'):
            stdin, stdout, stderr = ssh.exec_command(
                'dd if=/dev/sd' + i + ' of=/root/target_' + i + '.bin bs=512 skip=0 count=1 conv=fsync')
            while not stdout.channel.exit_status_ready():
                pass

        for i in ('b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l'):
            stdin, stdout, stderr = ssh.exec_command(
                'cat /root/target_' + i + '.bin')
            lines = stdout.channel.recv(2048)
            assert 'Test message is found! :D' in lines

        stdin, stdout, stderr = ssh.exec_command('rm /root/source.bin')
        while not stdout.channel.exit_status_ready():
            pass

        for i in ('b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l'):
            stdin, stdout, stderr = ssh.exec_command(
                'rm /root/target_' + i + '.bin')
            while not stdout.channel.exit_status_ready():
                pass

            stdin, stdout, stderr = ssh.exec_command(
                'ls /root' + i + '/target_' + i + '.bin')
            while not stdout.channel.exit_status_ready():
                pass

            lines = stdout.channel.recv(2048)
            assert 'target_' + i + '.bin' not in lines
