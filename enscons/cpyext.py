"""
Compiled extension support.
"""

from __future__ import print_function

import distutils.sysconfig, sysconfig, os

from distutils.core import Distribution
from distutils.extension import Extension
from distutils.command.build_ext import build_ext

def generate(env):
    # XXX extension generation is not finished
    env.Append(CPPPATH=[distutils.sysconfig.get_python_inc()])
    env.Append(LIBPATH=[distutils.sysconfig.get_config_var('LIBDIR')])
    # distutils doesn't link with -lpython<version> at least on OSX
    env.Append(LIBS=['python' + syscfg.get_config_var('py_version_short')])

    compiler = distutils.ccompiler.new_compiler()
    distutils.sysconfig.customize_compiler(compiler)
    if isinstance(compiler, distutils.unixccompiler.UnixCCompiler):
        env.MergeFlags(' '.join(compiler.compiler_so[1:]))

def generate_msvc(env):
    pass

# not used when enscons.generate is passed directly to Environment
def exists(env):
    return True

class no_build_ext(build_ext):
    # Are you kidding me? We have to run build_ext() to finish configuring the compiler.
    def build_extension(self, ext):
        def noop_spawn(*args):
            print(args)
        self.compiler.spawn = noop_spawn
        build_ext.build_extension(self, ext)

def get_build_ext(name='zoot'):
    """
    Naughty Zoot
    """

    tmp_dir = '/tmp/enscons'

    # from distutils.test.test_build_ext.py :
    xx_c = os.path.join(tmp_dir, 'xxmodule.c')
    xy_cpp = os.path.join(tmp_dir, 'xymodule.cc')
    xx_ext = Extension('xx', [xx_c, xy_cpp])
    dist = Distribution({'name': name, 'ext_modules': [xx_ext]})
    dist.package_dir = tmp_dir
    cmd = no_build_ext(dist)
    cmd.build_lib = tmp_dir
    cmd.build_temp = tmp_dir
    cmd.ensure_finalized()
    cmd.run()
    return cmd

def distutool(env):
    global ext # debugging

    # Compare compiler with ext.compiler.
    # Actually this has side effects adding redundant arguments to ext's compiler.
    # Could copy the compiler from ext before run() is called. 
    if False:
        compiler = distutils.ccompiler.new_compiler()
        distutils.sysconfig.customize_compiler(compiler)

    ext = get_build_ext()

    # Sanity checks that shared compiler startswith normal compiler?
    compiler = ext.compiler
    env.Replace(CC=compiler.compiler[0])
    env.Replace(CFLAGS=compiler.compiler[1:])
    env.Replace(CXX=compiler.compiler_cxx[0])
    env.Replace(LINKFLAGS=compiler.linker_exe[1:])
    env.Replace(SHLINKFLAGS=compiler.linker_so[1:])

    # rebuild LDMODULE? Better as a tool? Use SharedLibrary?

    # Some of these attributes are also available on ext
    env.Append(CPPPATH=compiler.include_dirs)
    env.Append(LIBPATH=compiler.library_dirs)

    # Interesting environment variables:
    # CC, CXX, AS, AR, RANLIB, CPPPATH, CCFLAGS, CXXFLAGS, LINKFLAGS

    # Windows will need env['ENV'] and basically is totally different 
    # as far as distutils is concerned; different class properties

def generate_scons_cpython(env):
    """
    Code from https://bitbucket.org/dirkbaechle/scons_cpython
    """
    #
    # Copyright (c) 2001-7,2010 The SCons Foundation
    #
    # Permission is hereby granted, free of charge, to any person obtaining
    # a copy of this software and associated documentation files (the
    # "Software"), to deal in the Software without restriction, including
    # without limitation the rights to use, copy, modify, merge, publish,
    # distribute, sublicense, and/or sell copies of the Software, and to
    # permit persons to whom the Software is furnished to do so, subject to
    # the following conditions:
    #
    # The above copyright notice and this permission notice shall be included
    # in all copies or substantial portions of the Software.
    #
    # THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY
    # KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
    # WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
    # NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
    # LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
    # OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
    # WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
    #
    from SCons.Tool.install import copyFunc

    try:
        env['INSTALL']
    except KeyError:
        env['INSTALL'] = copyFunc

    global PythonInstallBuilder
    PythonInstallBuilder = createPythonBuilder(env)

    py_version = '2.7'
    sys_version = sys.version_info[:2]
    if len(sys_version) == 2:
        py_version = '%d.%d' % (sys_version[0], sys_version[1])
    env.SetDefault(
        CPYTHON_PYC = 1, # generate '.pyc' files by default
        CPYTHON_EXE = 'python',
        CPYTHON_PYO_FLAGS = '-O',
        CPYTHON_PYO_CMD = "-c 'import sys,py_compile; [py_compile.compile(i) for i in sys.argv[1:]]'",
        CPYTHON_PYCOM = '$CPYTHON_EXE $CPYTHON_PYO_FLAGS $CPYTHON_PYO_CMD',
        CPYTHON_PYCOMSTR = 'Install file: "$SOURCE" as "$TARGET"',
        CPYTHON_SUFFIX = '.py', # extension for Python source files

        # Supporting variables for linking Boost.Python wrappers
        CPYTHON_VERSION = py_version,
        CPYTHON_INCLUDE = detect_python(env, py_version),
        CPYTHON_LIB = detect_python_lib(env, py_version),
        CPYTHON_BOOSTINC = '/usr/include',
        CPYTHON_BOOSTLIB = '/usr/lib'
    )
    
    env.AppendUnique(CXXFLAGS=['-fPIC'])
    env.Append(CPPPATH=['$CPYTHON_INCLUDE','$CPYTHON_BOOSTINC'])
    env.AppendUnique(LINKFLAGS=['-shared','-Wl,--export-dynamic'])
    env.Append(LIBPATH=['$CPYTHON_BOOSTLIB','$CPYTHON_LIB/config'])
    env.AppendUnique(LIBS=['boost_python','python$CPYTHON_VERSION'])

    try:
        env.AddMethod(InstallPython, "InstallPython")
    except AttributeError:
        # Looks like we use a pre-0.98 version of SCons...
        from SCons.Script.SConscript import SConsEnvironment
        SConsEnvironment.InstallPython = InstallPython
