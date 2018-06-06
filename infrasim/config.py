import os


def get_infrasim_root():
    if os.environ.get('INFRASIM_ROOT'):
        infrasim_root = os.environ['INFRASIM_ROOT']
    elif os.path.exists('/usr/local/infrasim'):
        infrasim_root = '/usr/local/infrasim'
    else:
        infrasim_root = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     os.path.pardir)

    return infrasim_root


# installed template
infrasim_template = os.path.join(get_infrasim_root(), "template")

# installed data
infrasim_data = os.path.join(get_infrasim_root(), "data")

# installed scripts
infrasim_scripts = os.path.join(get_infrasim_root(), "scripts")

# installed etc, just few examples there, after infrasim-init
# the initial configuration file will be put there
infrasim_etc = os.path.join(get_infrasim_root(), "etc")

# infrasim configuration file template, infrasim-init will render this template
infrasim_config_template = os.path.join(infrasim_template, "infrasim.yml")

# This is the infrasim home directory, most data and configuration file will be put here
infrasim_home = os.environ.get('INFRASIM_HOME') or os.path.join(os.environ['HOME'], ".infrasim")

# This is the infrasim chassis map directory, every chassis node mapping is restored here
infrasim_chassis_config_map = os.path.join(infrasim_home, ".chassis_map")

# This is the infrasim node map directory, every node mapping is restored here
infrasim_node_config_map = os.path.join(infrasim_home, ".node_map")

# inital configuration file after running infrasim-init
# and this is a copy for all the other nodes
infrasim_default_config = os.path.join(infrasim_node_config_map, "default.yml")

# infrasim log location
infrasim_log_dir = "/var/log/infrasim"
