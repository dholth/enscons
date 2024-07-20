"""
PEP 517 interface to enscons.

To be invoked by a future version of pip.

May not be possible to invoke more than one function without reloading Python.
"""

import os.path
import sys
import SCons.Script.Main


# optional hooks
#
# def get_build_wheel_requires(settings):
#     return []
#
# def get_build_sdist_requires(settings):
#     return []


def _run(alias):
    try:
        SCons.Script.Main.main()
    except SystemExit:
        pass
    # extreme non-api:
    lookup = SCons.Node.arg2nodes_lookups[0](alias).sources[0]
    return os.path.basename(str(lookup))


def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None):
    sys.argv[1:] = ["--wheel-dir=" + metadata_directory, "dist_info"]
    return _run("dist_info")


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    sys.argv[1:] = ["--wheel-dir=" + wheel_directory, "bdist_wheel"]
    return _run("bdist_wheel")


def build_sdist(sdist_directory, config_settings=None):
    sys.argv[1:] = ["--dist-dir=" + sdist_directory, "sdist"]
    return _run("sdist")


# PEP 660 editable installation
def build_editable(wheel_directory, config_settings=None, metadata_directory=None):
    sys.argv[1:] = ["--wheel-dir=" + wheel_directory, "editable"]
    return _run("editable")
