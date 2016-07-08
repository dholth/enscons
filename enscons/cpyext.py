"""
Compiled extension support.
"""

from __future__ import print_function

import distutils.sysconfig, sysconfig, os

from distutils.core import Distribution
from distutils.extension import Extension
from distutils.command.build_ext import build_ext

# not used when generate is passed directly to Environment
def exists(env):
    return True

class no_build_ext(build_ext):
    output = [] # for testing
    # Are you kidding me? We have to run build_ext() to finish configuring the compiler.
    def build_extension(self, ext):
        def noop_spawn(*args):
            no_build_ext.output.append(args)
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

def generate(env):
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
    env.Append(LIBS=compiler.libraries)

    # Interesting environment variables:
    # CC, CXX, AS, AR, RANLIB, CPPPATH, CCFLAGS, CXXFLAGS, LINKFLAGS

    # Windows will need env['ENV'] and basically is totally different 
    # as far as distutils is concerned; different class properties
