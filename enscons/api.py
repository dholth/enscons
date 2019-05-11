"""
PEP 517 interface to enscons.

To be invoked by a future version of pip.

May not be possible to invoke more than one function without reloading Python.
"""

import os.path
import sys
import SCons.Script.Main


def get_build_wheel_requires(settings):
    return []


def prepare_wheel_metadata(metadata_directory, settings):
    return  # basename of wheel...


def build_wheel(wheel_directory, settings, metadata_directory=None):
    sys.argv[1:] = ['--wheel-dir=' + wheel_directory, 'bdist_wheel']
    try:
        SCons.Script.Main.main()
    except SystemExit as e:
        pass
    for target in SCons.Script.DEFAULT_TARGETS:
        target_name = str(target)
        if target_name.endswith('.whl'):
            return os.path.basename(target_name)


def get_build_sdist_requires(settings):
    return []


def build_sdist(sdist_directory, settings):
    sys.argv[1:] = ['--dist-dir=' + sdist_directory, 'sdist']
    try:
        SCons.Script.Main.main()
    except SystemExit as e:
        pass
    for target in SCons.Script.DEFAULT_TARGETS:
        target_name = str(target)
        if target_name.endswith('.tar.gz'):
            return os.path.basename(target_name)
