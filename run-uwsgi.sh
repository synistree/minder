#!/bin/bash

pip install wheel
pip install uwsgi
uwsgi ./uwsgi.ini
