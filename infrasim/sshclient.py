'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''

from __future__ import print_function
import paramiko
import socket
import time
import datetime
import logging
logging.getLogger("paramiko").setLevel(logging.WARNING)


class SSH(object):

    def __init__(self, host, username, password, port=22, compression=True):
        self.ssh = None
        self.transport = None
        self.compression = compression
        self.buffer_size = 64 * 1024

        self.host_ip = host
        self.host_username = username
        self.host_pwd = password
        self.host_port = port

    def __del__(self):
        if self.transport is not None:
            self.transport.close()
            self.transport = None
            self.ssh.close()

    def connect(self, timeout=60):
        print("Connecting {username}@{host}:{port}"
                    .format(username=self.host_username,
                            host=self.host_ip,
                            port=self.host_port))
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        return self.reconnect(timeout)

    def reconnect(self, timeout=60):
        try:
            self.ssh.connect(self.host_ip, self.host_port, self.host_username,
                             self.host_pwd, timeout=timeout)
            self.transport = self.ssh.get_transport()
            self.transport.use_compression(self.compression)
        except socket.error as err:
            self.transport = None
            print("Failed to connect {host}: {err}".
                         format(host=self.host_ip, err=err))
        except paramiko.ssh_exception.BadAuthenticationType as err:
            self.transport = None
            print("Failed to connect {host}: {err}".
                         format(host=self.host_ip, err=err))
        except paramiko.ssh_exception.AuthenticationException as err:
            print("Failed to connect {host}: {err}".
                         format(host=self.host_ip, err=err))
        except paramiko.ssh_exception.BadHostKeyException as err:
            print("Failed to connect {host}: {err}".
                         format(host=self.host_ip, err=err))
        except Exception as ex:
            print("Failed to connect {}: {}".
                         format(self.host_ip, ex))
        return self.transport is not None

    def exec_command(self, cmd, indata=None, timeout=30):
        if self.transport is None or self.transport.is_active() is False:
            self.reconnect()
            if self.transport is None or self.transport.is_active() is False:
                print("Connection failed for executing command {}.".format(cmd))
                return -1, None

        input_data = self.__fix_indata(indata)

        try:
            session = self.transport.open_session()
            session.set_combine_stderr(True)
            session.get_pty()
            session.exec_command(cmd)
        except paramiko.SSHException as ex:
            print("Exception for command '{0}: {1}'".format(cmd, ex))
            session.close()
            return -1, None
        output = self.poll(session, timeout, input_data)
        status = session.recv_exit_status()
        session.close()
        return status, output

    def connected(self):
        return self.transport is not None

    def __fix_indata(self, indata):
        if indata is not None:
            if len(indata) > 0:
                if '\\n' in indata:
                    lines = indata.split('\\n')
                    indata = '\n'.join(lines)
            return indata.split('\n')
        return []

    def poll(self, session, timeout=30, indata=[]):
        session.setblocking(0)
        index = 0
        timeout_flag = False
        start = time.mktime(datetime.datetime.now().timetuple())
        output = ''
        while True:
            if session.recv_ready():
                data = session.recv(self.buffer_size)
                output += data

                if session.send_ready():
                    if index < len(indata):
                        data = indata[index] + '\n'
                        index += 1
                        print("sending {0} bytes data".format(len(data)))
                        session.send(data)

            if session.exit_status_ready():
                break

            now = time.mktime(datetime.datetime.now().timetuple())
            delta = now - start

            if delta > timeout:
                timeout_flag = True
                break

            time.sleep(0.5)

        if session.recv_ready():
            data = session.recv(self.buffer_size)
            output += data
            print("1: Got {0} bytes, total {1} bytes".
                        format(len(data), len(output)))

        if timeout_flag:
            output += '\nError: timeout after {0} seconds\n'.format(timeout)

        return output
