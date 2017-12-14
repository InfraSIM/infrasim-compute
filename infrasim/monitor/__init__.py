#!/usr/bin/env python

from flask import Flask
from .apis import api
from .apis.qmp import ns as qmp_ns
from .apis.hmp import ns as hmp_ns
from .apis.admin import ns as admin_ns
from infrasim.monitor import monitor_logger
import logging

app = Flask(__name__)

def start(instance, host, port):
    api.add_namespace(qmp_ns)
    api.add_namespace(hmp_ns)
    api.add_namespace(admin_ns)

    mlog = monitor_logger.init_logger(instance)
    mlog.setLevel(logging.DEBUG)
    app.logger.addHandler(mlog.handlers)

    api.init_app(app)
    app.run(host=host, port=port)
