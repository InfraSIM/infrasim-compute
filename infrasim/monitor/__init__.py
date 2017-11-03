#!/usr/bin/env python

from flask import Flask
from .apis import api
from .apis.qmp import ns as qmp_ns
from .apis.hmp import ns as hmp_ns
from .apis.admin import ns as admin_ns


app = Flask(__name__)


api.add_namespace(qmp_ns)
api.add_namespace(hmp_ns)
api.add_namespace(admin_ns)
api.init_app(app)
