Infrasim-compute: bare-metal server simulator
---------------------------------------------

|Version| |Downloads|

System Basic Requirements
-------------------------

Infrasim package can be installed in any physical machine or virtual
machines hosted by Virtualbox, ESXi, Parallel Desktop or cloud provider
like AWS, Linode and etc.

The basic installation system requirements are:

1. Ubuntu Linux 64bit OS (14.04/15.04/16.04)

2. at least 4GB memory

3. at least 16GB disk size

Installation
------------

1. Ensure sources.list integrity then install dependency:

   ::

       sudo apt-get update
       sudo apt-get install python-pip libpython-dev libssl-dev

2. Upgrade pip and install setuptools:

   ::

       sudo pip install --upgrade pip
       sudo pip install setuptools

3. Two ways to install infrasim:

   -  install infrasim from source code:

      ::

          git clone https://github.com/InfraSIM/infrasim-compute.git

          cd infrasim-compute

          sudo pip install -r requirements.txt

          sudo python setup.py install

   -  install infrasim from python library:

      ::

          sudo pip install infrasim-compute

Start Infrasim Service
----------------------

1. Initialization (you need do it once)

   ::

       sudo infrasim init

   Optional arguments:

   -  -s, --skip-installation Ignore qemu/openipmi package installation

   -  -c [CONFIG\_FILE], --config-file [CONFIG\_FILE] Use customized
      yaml file for the default node

   -  -t [TYPE], --type [TYPE] Render specified node type for the
      default node

2. Infrasim Service Version:

   ::

       sudo infrasim version

3. Infrasim Node Configuration Management:

   -  Add configuration mapping to a node

   ::

       sudo infrasim config add <node name> <config path>

   -  Delete configuration mapping of a node

   ::

       sudo infrasim config delete <node name>

   -  Update configuration mapping of a node

   ::

       sudo infrasim config update <node name> <config path>

   -  List all configuration mappings

   ::

       sudo infrasim config list

4. Infrasim Service Node Commands

   -  Start a node

   ::

       sudo infrasim node start [node name]

   -  Check node status

   ::

       sudo infrasim node status [node name]

   -  Stop a node

   ::

       sudo infrasim node stop [node name]

   -  Restart a node

   ::

       sudo infrasim node restart [node name]

   -  Stop a node and detroy its runtime workspace

   ::

       sudo infrasim node destroy [node name]

   The default node configuration is already added to configuration
   mapping during **infrasim init**. In node commands, argument [node
   name] is optional. If it's not specified, it's treated as node
   "default".

**Notice: You can use VNC to access the emulated legacy hardware, the
default VNC port is 5901**

.. |Version| image:: https://img.shields.io/pypi/v/infrasim-compute.svg
   :target: https://pypi.python.org/pypi/infrasim-compute
.. |Downloads| image:: https://img.shields.io/pypi/dm/infrasim-compute.svg
   :target: https://pypi.python.org/pypi/infrasim-compute
