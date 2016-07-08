#!/usr/bin/env python
# Call enscons to emulate setup.py, installing if necessary.

import sys, subprocess, pkg_resources

sys.path[0:0] = ['setup-requires']

try:
    import enscons.setup
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", 
        "-t", "setup-requires", "enscons"])
    import enscons.setup

enscons.setup.setup()

