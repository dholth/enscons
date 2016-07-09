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
    if not hasattr(compiler, 'compiler'):   # assume Windows
        return generate_msvc(env, compiler)

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

def generate_msvc(env, compiler):
    """
    Set SCons environment from distutils msvc9compiler
    """
    import pprint
    pprint.pprint(compiler.__dict__)
    # Python 2.7 distutils does not find full compiler path.
    # Ask Environment for correct MSVC during creation.
    env.Replace(CC=env.File(compiler.cc))   # File helps with spaces
    env.Replace(CFLAGS=compiler.compile_options)
    env.Replace(CXX=env.File(compiler.cc))
    env.Replace(LINK=env.File(compiler.linker))   # see mslink
    env.Replace(LINKFLAGS=compiler.ldflags_static)
    env.Replace(SHLINKFLAGS=compiler.ldflags_shared)    # see also ldflags_shared_debug
    env.Replace(RC=env.File(compiler.rc))

    # rebuild LDMODULE? Better as a tool? Use SharedLibrary?

    # Some of these attributes are also available on ext
    env.Append(CPPPATH=compiler.include_dirs)
    env.Append(LIBPATH=compiler.library_dirs)
    env.Append(LIBS=compiler.libraries)
