#!/usr/bin/env python
from flask import Flask
from .redfishsim.apis import api

app = Flask(__name__)
api.init_app(app)

def start(instance="default", host="0.0.0.0", port=8080):
    app.run(host=host, port=int(port,10), debug=True)

if __name__ == "__main__":
    start()
