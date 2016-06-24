"""
Compiled extension support.
"""

def generate(env):
    # XXX extension generation is not finished
    env.Append(CPPPATH=[sysconfig.get_python_inc()])
    env.Append(LIBPATH=[sysconfig.get_config_var('LIBDIR')])
    # LIBS = ['python' + sysconfig.get_config_var('VERSION')] # only on CPython; ask distutils

    compiler = distutils.ccompiler.new_compiler()
    distutils.sysconfig.customize_compiler(compiler)
    if isinstance(compiler, distutils.unixccompiler.UnixCCompiler):
        env.MergeFlags(' '.join(compiler.compiler_so[1:]))
        # XXX other flags are revealed in compiler
    # XXX MSVC works differently
    
def exists(env):
    return True

