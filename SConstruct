# Wheel generation from SCons.
#
# Daniel Holth <dholth@gmail.com>, 2016
#
# The MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

import pytoml as toml
import enscons
import sys

metadata = dict(toml.load(open('pyproject.toml')))['tool']['enscons']

full_tag = 'py2.py3-none-any'

env = Environment(tools=['default', 'packaging', enscons.generate],
                  PACKAGE_METADATA=metadata,
                  WHEEL_TAG=full_tag,
                  )

py_source = Glob('enscons/*.py')

sdist = env.SDist(source=FindSourceFiles() + ['PKG-INFO', 'setup.py', 'README.rst', 'CHANGES'])
env.NoClean(sdist)
env.Alias('sdist', sdist)

purelib = env.Whl('purelib', py_source, root='.')
whl = env.WhlFile(purelib)

install = env.Command("#DUMMY", whl,
    ' '.join([sys.executable, '-m', 'pip', 'install', '--no-deps', '$SOURCE']))
env.Alias('install', install)
env.AlwaysBuild(install)

env.Default(whl, sdist)
