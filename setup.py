#!/usr/bin/env python
# Call enscons to emulate setup.py, installing if necessary.

import sys, subprocess, os.path

sys.path[0:0] = ['setup-requires']

try:
    import enscons.setup
except ImportError:
    requires = ["import_scons", "pytoml"] # just ["enscons"] for enscons users
    subprocess.check_call([sys.executable, "-m", "pip", "install", 
        "-t", "setup-requires"] + requires)
    del sys.path_importer_cache['setup-requires'] # needed if setup-requires was absent
    import enscons.setup

enscons.setup.setup()

