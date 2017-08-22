"""
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
"""
import unittest
import os
import yaml
import time
import paramiko
import subprocess
import re
from infrasim import model
from infrasim import run_command
from infrasim import helper
from test import fixtures

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
    global sas_drive_serial
    global sata_drive_serial
    global boot_drive_serial
    sas_drive_serial = "20160518AA851134100"
    sata_drive_serial = "20160518AA851134101"
    boot_drive_serial = "20160518AA851134102"
    test_img_file = '/tmp/kcs.img'
    tmp_conf_file = '/tmp/test.yml'
    conf = {}
    format_f = False

    def get_drive(self, serial):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        paramiko.util.log_to_file("filename.log")
        helper.try_func(600, paramiko.SSHClient.connect, ssh, "127.0.0.1",
                        port=2222, username="root", password="root", timeout=120)
        stdin, stdout, stderr = ssh.exec_command("ls /dev")
        drives = stdout.channel.recv(2048)
        drives = [e for e in filter(lambda x:"sd" in x, drives.split())]

        for drive in drives:
            stdin, stdout, stderr = ssh.exec_command('sg_inq /dev/'+drive)
            lines = stdout.channel.recv(2048)
            if serial in lines:
                return drive


    def start_node(self):
        global conf
        global sas_drive_serial
        global sata_drive_serial
        global boot_drive_serial
        fake_config = fixtures.FakeConfig()
        conf = fake_config.get_node_info()
        conf['compute']['storage_backend'] = [{
            'type': 'ahci',
            'max_drive_per_controller': 6,
            'drives': [
                {'size': 8, 'file': test_img_file, 'boot_index': 1, 'serial': boot_drive_serial},
                {'size': 4, 'file': '/tmp/sdb.img', 'format': 'raw', 'serial': sata_drive_serial},
                {'size': 8, 'file': '/tmp/sdc.img', 'format': 'raw'},
                {'size': 8, 'file': '/tmp/sdd.img', 'format': 'raw'},
                {'size': 8, 'file': '/tmp/sde.img', 'format': 'raw'},
                {'size': 8, 'file': '/tmp/sdf.img', 'format': 'raw'}
            ]
        },
            {
            'type': 'megasas-gen2',
            'max_drive_per_controller': 6,
            'drives': [
                {'size': 4, 'file': '/tmp/sdg.img', 'format': 'raw', 'serial': sas_drive_serial},
                {'size': 8, 'file': '/tmp/sdh.img', 'format': 'raw'},
                {'size': 8, 'file': '/tmp/sdi.img', 'format': 'raw'},
                {'size': 8, 'file': '/tmp/sdj.img', 'format': 'raw'},
                {'size': 8, 'file': '/tmp/sdk.img', 'format': 'raw'},
                {'size': 8, 'file': '/tmp/sdl.img', 'format': 'raw'}]
        }]

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
        MD5_KCS_IMG = '986e5e63e8231a307babfbe9c81ca210'
        helper.fetch_image(DOWNLOAD_URL, MD5_KCS_IMG, test_img_file)

        cls.start_node()
        cls.port_forward()


    def tearDown(cls):
        if conf:
            cls.stop_node()
        for i in range(97, 109):
            disk_file = "/tmp/sd{}.img".format(chr(i));
            if os.path.exists(disk_file):
                os.unlink(disk_file)

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
        global conf
        # Write disk
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
        # FIXME
        ssh = self.prepare_ssh()
        drive = self.get_drive(sas_drive_serial)
        stdin, stdout, stderr = ssh.exec_command(
            'dd if=/root/source.bin of=/dev/'+drive+' bs=512 seek=0 count=1 conv=fsync')
        while not stdout.channel.exit_status_ready():
            pass

        ssh.close()

        # Check disk content intact after node restart
        run_command("infrasim node restart {}".format(conf["name"]))
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
            'dd if=/dev/'+drive+' of=/root/target.bin bs=512 skip=0 count=1 conv=fsync')
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
        ssh.close()
        assert 'source.bin' not in lines

    def test_copy_file_across_drives(self):
        ssh = self.prepare_ssh()
        stdin, stdout, stderr = ssh.exec_command('touch /root/source.bin')
        while not stdout.channel.exit_status_ready():
            pass

        stdin, stdout, stderr = ssh.exec_command(
            "echo 'Test message is found! :D' >> /root/source.bin")
        while not stdout.channel.exit_status_ready():
            pass
        drive = self.get_drive(boot_drive_serial)
        for i in ('a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l'):
            if 'sd'+i != drive:
                stdin, stdout, stderr = ssh.exec_command(
                    'dd if=/root/source.bin of=/dev/sd' + i + ' bs=512 seek=0 count=1 conv=fsync')
        ssh.close()

        ssh = self.prepare_ssh()
        boot_drive = self.get_drive(boot_drive_serial)
        sas_drive = self.get_drive(sas_drive_serial)
        sata_drive = self.get_drive(sata_drive_serial)
        for i in ('a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l'):
            if 'sd'+i not in[boot_drive, sas_drive, sata_drive] :
                stdin, stdout, stderr = ssh.exec_command(
                    'dd if=/dev/sd' + i + ' of=/root/target_' + i + '.bin bs=512 skip=0 count=1 conv=fsync')
        for i in ('a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l'):
            if 'sd'+i not in[boot_drive, sas_drive, sata_drive] :
                stdin, stdout, stderr = ssh.exec_command(
                    'cat /root/target_' + i + '.bin')
                lines = stdout.channel.recv(2048)
                assert 'Test message is found! :D' in lines
        ssh.close()

        ssh = self.prepare_ssh()
        stdin, stdout, stderr = ssh.exec_command('rm /root/source.bin')
        while not stdout.channel.exit_status_ready():
            pass
        boot_drive = self.get_drive(boot_drive_serial)
        sas_drive = self.get_drive(sas_drive_serial)
        sata_drive = self.get_drive(sata_drive_serial)
        for i in ('a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l'):
            if 'sd'+i not in[boot_drive, sas_drive, sata_drive] :
                stdin, stdout, stderr = ssh.exec_command(
                    'rm /root/target_' + i + '.bin')

                stdin, stdout, stderr = ssh.exec_command(
                    'ls /root' + i + '/target_' + i + '.bin')

                lines = stdout.channel.recv(2048)
                assert 'target_' + i + '.bin' not in lines
        ssh.close()

    def test_sas_drive_erase(self):
        # Only format 1 sas drive here.
        # Otherwise, it will take long time which is not suitable for functional test.
        global sas_drive_serial
        ssh = self.prepare_ssh()
        stdin, stdout, stderr = ssh.exec_command('echo abcdefg > test_file')
        while not stdout.channel.exit_status_ready():
            pass
        drive = self.get_drive(sas_drive_serial)
        stdin, stdout, stderr = ssh.exec_command(
            'dd if=test_file of=/dev/'+drive+' bs=10M seek=8388607 count=1 conv=fsync')
        while not stdout.channel.exit_status_ready():
            pass
        ssh.exec_command('rm -rf test_file')
        ssh.close()

        ssh = self.prepare_ssh()

        # Check disk size, which should be 4GB
        stdin, stdout, stderr = ssh.exec_command('sg_readcap /dev/' + drive)
        while not stdout.channel.exit_status_ready():
            pass
        lines = stdout.channel.recv(2048)
        assert "Device size: 4294967296 bytes, 4096.0 MiB, 4.29 GB" in lines

        stdin, stdout, stderr = ssh.exec_command(
            'sg_format --format /dev/'+drive)
        while not stdout.channel.exit_status_ready():
            pass

        while True:
            stdin, stdout, stderr = ssh.exec_command(
                'sg_requests -p /dev/'+drive)
            while not stdout.channel.exit_status_ready():
                pass
            lines = stdout.channel.recv(2048)
            # Expects format complete, and no "Progress indication" message from "sg_requests"
            if 'Progress indication' in lines:
                time.sleep(1)
            else:
                break

        stdin, stdout, stderr = ssh.exec_command('dd if=/dev/{} skip=8388607 count=1 | hexdump -C'.format(drive))
        lines = stdout.channel.recv(2048)
        print "hexdump result after formating:\r\n", lines
        # Expects hexdump shows drive data in the last sector is all zero. That is something like below:
        # 00000000  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
        # *
        # 00000200
        assert re.match(r"00000000  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|\*\00000200", lines)

    def test_sata_drive_erase_master_pw(self):
        # Only format 1 sata drive here.
        # Otherwise, it will take long time which is not suitable for functional test.
        ssh = self.prepare_ssh()
        global sata_drive_serial
        drive = self.get_drive(sata_drive_serial)
        # Set master password
        master_pw = "master_password"
        stdin, stdout, stderr = ssh.exec_command('hdparm --user-master m --security-set-pass '+master_pw+' /dev/'+drive)

        # Set user password and check if "Security Mode feature set" enabled.
        usr_pw = "user_password"
        stdin, stdout, stderr = ssh.exec_command('hdparm --security-set-pass '+usr_pw+' /dev/'+drive)

        stdin, stdout, stderr = ssh.exec_command('hdparm -I /dev/'+drive)
        lines = stdout.channel.recv(2048)
        print 'hdparm -I /dev/'+drive+'\r\n', lines
        assert re.search(r"\*\s+Security Mode feature set", lines)
        assert re.search(r"\s+device size with M = 1024\*1024:\s+4096 MBytes", lines)

        ssh.close()

        ssh = self.prepare_ssh()
        # Write disk
        stdin, stdout, stderr = ssh.exec_command('echo abcdefg > test_file')
        stdin, stdout, stderr = ssh.exec_command(
            'dd if=test_file of=/dev/'+drive+' bs=10M seek=8388607 count=1 conv=fsync')
        ssh.exec_command('rm -rf test_file')
        # Erase disk
        stdin, stdout, stderr = ssh.exec_command('hdparm --user-master m --security-erase '+master_pw+' /dev/'+drive)
        while not stdout.channel.exit_status_ready():
            pass
        stdin, stdout, stderr = ssh.exec_command('dd if=/dev/{} skip=8388607 count=1 | hexdump -C'.format(drive))
        lines = stdout.channel.recv(2048)
        print "hexdump result after formating:\r\n", lines
        # Expects hexdump shows drive data in the last sector is all zero. That is something like below:
        # 00000000  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
        # *
        # 00000200
        assert re.match(r"00000000  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|\*\00000200", lines)

        stdin, stdout, stderr = ssh.exec_command('hdparm -I /dev/'+drive)
        lines = stdout.channel.recv(2048)
        ssh = self.prepare_ssh()

        assert re.search(r"\*\s+Security Mode feature set", lines) is None

    def test_sata_drive_erase_usr_pw(self):
        # Only format 1 sata drive here.
        # Otherwise, it will take long time which is not suitable for functional test.
        ssh = self.prepare_ssh()
        drive = self.get_drive(sata_drive_serial)
        stdin, stdout, stderr = ssh.exec_command('hdparm -I /dev/'+drive)
        lines = stdout.channel.recv(2048)
        assert re.search(r"\*\s+Security Mode feature set", lines) is None

        usr_pw = "user_password"
        stdin, stdout, stderr = ssh.exec_command('hdparm --security-set-pass '+usr_pw+' /dev/'+drive)

        stdin, stdout, stderr = ssh.exec_command('hdparm -I /dev/'+drive)
        lines = stdout.channel.recv(2048)
        # Expect "Security Mode feature set" to be enabled after set user password
        print "hdparm -I /dev/'"+drive+'\r\n', lines
        assert re.search(r"\*\s+Security Mode feature set", lines)
        assert re.search(r"\s+device size with M = 1024\*1024:\s+4096 MBytes", lines)

        ssh.close()

        ssh = self.prepare_ssh()
        stdin, stdout, stderr = ssh.exec_command('echo abcdefg > test_file')
        while not stdout.channel.exit_status_ready():
            pass
        ssh.close()

        ssh = self.prepare_ssh()

        # Write to the last block of drive
        stdin, stdout, stderr = ssh.exec_command(
            'dd if=test_file of=/dev/'+drive+' bs=10M seek=8388607 count=1 conv=fsync')

        ssh.exec_command('rm -rf test_file')

        stdin, stdout, stderr = ssh.exec_command('hdparm --user-master u --security-erase '+usr_pw+' /dev/'+drive)
        while not stdout.channel.exit_status_ready():
            pass
        stdin, stdout, stderr = ssh.exec_command('dd if=/dev/{} skip=8388607 count=1 | hexdump -C'.format(drive))
        lines = stdout.channel.recv(2048)

        # Expects hexdump shows drive data in the last sector is all zero. That is something like below:
        # 00000000  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
        # *
        # 00000200
        print "hexdump result after formating:\r\n", lines
        assert re.match(r"00000000  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|\*\00000200", lines)

        stdin, stdout, stderr = ssh.exec_command('hdparm -I /dev/'+drive)
        lines = stdout.channel.recv(2048)
        # Expect "Security Mode feature set" to be disabled
        assert re.search(r"\*\s+Security Mode feature set", lines) is None
        ssh.close()
