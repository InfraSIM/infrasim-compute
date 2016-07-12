Infrasim-compute: bare-metal server simulator
-----------------------------------------------------

.. image:: https://img.shields.io/pypi/v/nine.svg?maxAge=2592000   :target: https://pypi.python.org/pypi/infrasim-compute

.. image:: https://img.shields.io/pypi/dm/Django.svg?maxAge=2592000   :target: https://pypi.python.org/pypi/infrasim-compute

System Basic Requirements
-------------------------
Infrasim package can be installed in any physical machine or virtual machines hosted by Virtualbox, ESXi, Parallel Desktop or cloud provider like AWS, Linode and etc.

The basic installation system requirements are:
    1.  Ubuntu Linux 64bit OS (14.04/15.04/16.04)
    2.  at least 4GB memory
    3.  at least 16GB disk size

Installation
------------

1. Install dependency:
    **sudo apt-get install socat ipmitool qemu openipmi python-pip libssl-dev libssh-dev libpython-dev**

2. For Ubuntu 14.04/15.04, upgrade pip:
    ** sudo pip install --upgrade pip**

3. Install infrasim
    **sudo pip install infrasim-compute**


Start Infrasim Service
----------------------

1. Initialization (you need do it once)
    **sudo infrasim-init**

2. Start Infrasim Service
    **sudo inframsim-main start**

3. Stop Infrasim Service
    **sudo infrasim-main stop**

**Notice: You can use VNC to access the emulated legacy hardware, the default VNC port is 5901**

Configure Infrasim
-------------------

You can configure your own legacy hardware through **/etc/infrasim/infrasim.conf**.
