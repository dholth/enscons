#!/usr/bin/env python
# Call enscons to emulate setup.py, installing if necessary.
# (this setup.py can be copied into any enscons-powered project by editing requires=)

import sys
import subprocess

sys.path[0:0] = ["setup-requires"]

try:
    import enscons.setup
except ImportError:
    requires = [
        "scons>=3.0.5",
        "tomllib; python_version<'3.11'",
    ]  # just ["enscons"] for enscons users
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-t", "setup-requires"] + requires
    )
    del sys.path_importer_cache["setup-requires"]  # needed if setup-requires was absent
    import enscons.setup

enscons.setup.setup()
