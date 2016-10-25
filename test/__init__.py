import os
from infrasim import config

if not os.path.exists(config.infrasim_home):
    os.mkdir(config.infrasim_home)
