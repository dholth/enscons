"""
Compiled extension support.
"""

from __future__ import print_function

import distutils.sysconfig, sysconfig, os, os.path

from distutils.core import Distribution
from distutils.extension import Extension
from distutils.command.build_ext import build_ext

import imp
import importlib

# not used when generate is passed directly to Environment
def exists(env):
    return True


def extension_filename(modname, abi3=False):
    """
    Return the path for a new extension.

    Given the Python dot-separated modname "a.b.c", return e.g.
    "a/b/c.cpython-xyz.so".

    If abi3=True and supported by the interpreter, return e.g.
    "a/b/c.abi3.so".
    """
    from distutils.sysconfig import get_config_var

    # we could probably just split modname by '.' instead of using ext here:
    ext = get_build_ext()
    fullname = ext.get_ext_fullname(modname)
    modpath = fullname.split(".")
    ext_filename = os.path.join(*modpath)

    suffix = None
    try:
        suffixes = importlib.machinery.EXTENSION_SUFFIXES
        suffix = suffixes[0] if suffixes else None
    except AttributeError:
        pass
    if not suffix:
        suffix = get_config_var("EXT_SUFFIX")
    if not suffix:
        suffix = get_config_var("SO")  # py2

    if abi3:
        suffix = get_abi3_suffix() or suffix

    return ext_filename + suffix


class no_build_ext(build_ext):
    output = []  # for testing
    # Are you kidding me? We have to run build_ext() to finish configuring the compiler.
    def build_extension(self, ext):
        def noop_spawn(*args):
            no_build_ext.output.append(args)

        self.compiler.spawn = noop_spawn
        build_ext.build_extension(self, ext)


def get_build_ext(name="zoot"):
    """
    Naughty Zoot
    """

    tmp_dir = "/tmp/enscons"

    # from distutils.test.test_build_ext.py :
    xx_c = os.path.join(tmp_dir, "xxmodule.c")
    xy_cpp = os.path.join(tmp_dir, "xymodule.cc")
    xx_ext = Extension("xx", [xx_c, xy_cpp])
    dist = Distribution({"name": name, "ext_modules": [xx_ext]})
    dist.package_dir = tmp_dir
    cmd = no_build_ext(dist)
    cmd.build_lib = tmp_dir
    cmd.build_temp = tmp_dir
    cmd.ensure_finalized()
    cmd.run()
    return cmd


# from setuptools
def get_abi3_suffix():
    """Return the file extension for an abi3-compliant Extension()"""
    for suffix, _, _ in (s for s in imp.get_suffixes() if s[2] == imp.C_EXTENSION):
        if ".abi3" in suffix:  # Unix
            return suffix
        elif suffix == ".pyd":  # Windows
            return suffix


def generate(env):
    global ext  # debugging

    # Compare compiler with ext.compiler.
    # Actually this has side effects adding redundant arguments to ext's compiler.
    # Could copy the compiler from ext before run() is called.
    if False:
        compiler = distutils.ccompiler.new_compiler()
        distutils.sysconfig.customize_compiler(compiler)

    ext = get_build_ext()

    # Sanity checks that shared compiler startswith normal compiler?
    compiler = ext.compiler
    if not hasattr(compiler, "compiler"):  # assume Windows
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
    env.Replace(CC=env.File(compiler.cc))  # File helps with spaces
    env.Replace(CFLAGS=compiler.compile_options)
    env.Replace(CXX=env.File(compiler.cc))
    env.Replace(LINK=env.File(compiler.linker))  # see mslink
    env.Replace(LINKFLAGS=compiler.ldflags_static)
    env.Replace(SHLINKFLAGS=compiler.ldflags_shared)  # see also ldflags_shared_debug
    env.Replace(RC=env.File(compiler.rc))

    # rebuild LDMODULE? Better as a tool? Use SharedLibrary?

    # Some of these attributes are also available on ext
    env.Append(CPPPATH=compiler.include_dirs)
    env.Append(LIBPATH=compiler.library_dirs)
    env.Append(LIBS=compiler.libraries)
