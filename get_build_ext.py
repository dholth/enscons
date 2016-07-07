import setuptools
import enscons.cpyext
from enscons.cpyext import get_build_ext

import distutils.ccompiler, distutils.sysconfig

# Which env variables must be overridden?
from SCons.Script import *
env = Environment(tools=['default', enscons.cpyext.distutool])