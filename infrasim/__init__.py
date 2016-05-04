#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

logger = logging.getLogger('infrasim')
hdlr = logging.FileHandler('/var/tmp/inframsim.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.WARNING)
