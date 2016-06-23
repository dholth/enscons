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

# This SConstruct and the bdist tool are released under the MIT license;
# the pysdl2-cffi binding is GPL.

from __future__ import unicode_literals, print_function

from distutils import sysconfig
from SCons.Script import Copy, Action, FindInstalledFiles
import distutils.ccompiler, distutils.sysconfig, distutils.unixccompiler
import wheel.metadata
import os.path
import codecs
from pkg_resources import safe_name, safe_version, to_filename, safe_extra

def normalize_package(name):
    # XXX encourage project names to start out 'safe'
    return to_filename(safe_name(name))

def convert_requirements(requirements, extras):
    """
    Convert requirements from a setup()-style dictionary to Requires-Dist
    and Provides-Extra.
    """
    # XXX this could be copied back into wheel
    extras[''] = requirements
    for extra, depends in extras.items():
        condition = ''
        if extra and ':' in extra:  # setuptools extra:condition syntax
            extra, condition = extra.split(':', 1)
        if extra:
            yield ('Provides-Extra', extra)
            if condition:
                condition += " and "
            condition += "extra == '%s'" % extra    # assume extra is already safe_extra()
        if condition:
            condition = '; ' + condition
        for new_req in sorted(wheel.metadata.convert_requirements(depends)):
            yield ('Requires-Dist', new_req + condition)

def egg_info_targets(env):
    """
    Write the minimum .egg-info for pip. Full metadata will go into wheel's .dist-info
    """
    return [env.fs.Dir(env['EGG_INFO_PATH']).File(name)
            for name in ['PKG-INFO', 'requires.txt']]

import setuptools.command.egg_info

class Command(object):
    """Mock object to allow setuptools to write files for us"""
    def __init__(self, distribution):
        self.distribution = distribution

    def write_or_delete_file(self, basename, filename, data):
        self.data = data

class Distribution(object):
    def __init__(self, metadata):
        self.__dict__ = metadata

def egg_info_builder(target, source, env):
    """
    Minimum egg_info. To be used only by pip to get dependencies.
    """
    command = env['DUMMY_COMMAND']
    for dnode in target:
        with open(dnode.get_path(), 'w') as f:
            if dnode.name == 'PKG-INFO':
                f.write("Metadata-Version: 1.1\n")
                f.write("Name: %s\n" % env['PACKAGE_NAME'])
                f.write("Version: %s\n" % env['PACKAGE_VERSION'])
            elif dnode.name == "requires.txt":
                setuptools.command.egg_info.write_requirements(command, dnode.name, 'spamalot')
                f.write(command.data)

def metadata_builder(target, source, env):
    metadata = env['PACKAGE_METADATA']
    with codecs.open(target[0].get_path(), mode='w', encoding='utf-8') as f:
        f.write("Metadata-Version: 2.0\n")
        f.write("Name: %s\n" % metadata['name'])
        f.write("Version: %s\n" % metadata['version'])
        f.write("Sumary: %s\n" % metadata['description'])
        f.write("Home-Page: %s\n" % metadata['url'])
        f.write("Author: %s\n" % metadata['author'])
        f.write("Author-email: %s\n" % metadata['author_email'])
        f.write("License: %s\n" % metadata['license'])
        f.write("Keywords: %s\n" % " ".join(metadata['keywords']))
        f.write("Platform: %s\n" % metadata.get('platform', 'UNKNOWN'))
        for classifier in metadata.get('classifiers', []):
            f.write("Classifier: %s\n" % classifier)
        for requirement in convert_requirements(metadata.get('install_requires', []),
                                                metadata.get('extras_require', {})):
            f.write("%s: %s\n" % requirement)

        # XXX long description

import base64

def urlsafe_b64encode(data):
    """urlsafe_b64encode without padding"""
    return base64.urlsafe_b64encode(data).rstrip(b'=')

def add_manifest(target, source, env):
    """
    Add the wheel manifest.
    """
    import hashlib
    import zipfile
    archive = zipfile.ZipFile(target[0].get_path(), 'a')
    lines = []
    for f in archive.namelist():
        print("File: %s" % f)
        data = archive.read(f)
        size = len(data)
        digest = hashlib.sha256(data).digest()
        digest = "sha256=" + (urlsafe_b64encode(digest).decode('ascii'))
        lines.append("%s,%s,%s" % (f.replace(',', ',,'), digest, size))

    record_path = env['DIST_INFO_PATH'].get_path(dir=env['WHEEL_PATH']) + '/RECORD'
    lines.append(record_path + ',,')
    RECORD = '\n'.join(lines)
    archive.writestr(record_path, RECORD)
    archive.close()

def wheelmeta_builder(target, source, env):
    with open(target[0].get_path(), 'w') as f:
        f.write("""Wheel-Version: 1.0
Generator: enscons (0.0.1)
Root-Is-Purelib: false
Tag: %s
""" % env['WHEEL_TAG'])

def exists(env):
    return True

def Whl(env, category, source, root=None):
    """
    Copy wheel members into their archive locations.
    """
    target_dir = env['WHEEL_DATA_PATH'].Dir(category).get_path()
    for node in source:
        relpath = os.path.relpath(node.get_path(), root or '')
        args = (os.path.join(target_dir, relpath), node)
        env.InstallAs(*args)

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

    env['PACKAGE_NAME'] = env['PACKAGE_METADATA']['name']
    env['PACKAGE_NAME_SAFE'] = normalize_package(env['PACKAGE_NAME'])
    env['PACKAGE_VERSION'] = env['PACKAGE_METADATA']['version']

    # Development .egg-info has no version number. Needs to have
    # underscore _ and not hyphen -
    env['EGG_INFO_PATH'] = env['PACKAGE_NAME_SAFE'] + '.egg-info'
    if env['EGG_INFO_PREFIX']:
        env['EGG_INFO_PATH'] = env.Dir(env['EGG_INFO_PREFIX']).Dir(env['EGG_INFO_PATH'])
    
    # all files under this directory will be packaged as a wheel
    env['WHEEL_PATH'] = env.Dir('#build/wheel/')
    
    env['DIST_INFO_PATH'] = env['WHEEL_PATH'].Dir(env['PACKAGE_NAME_SAFE']
                                                  + '-' + env['PACKAGE_VERSION'] + '.dist-info')
    env['WHEEL_DATA_PATH'] = env['WHEEL_PATH'].Dir(env['PACKAGE_NAME_SAFE'] 
                                                   + '-' + env['PACKAGE_VERSION'] + '.data')

    env.Command(env['DIST_INFO_PATH'].File('WHEEL'), 'pyproject.toml', wheelmeta_builder)

    # this distutils command helps trick setuptools into doing work for us
    command = Command(Distribution(env['PACKAGE_METADATA']))
    egg_info = env.Command(egg_info_targets(env),
                           'pyproject.toml',
                           egg_info_builder)
    env['DUMMY_COMMAND'] = command

    env.Clean(egg_info, env['EGG_INFO_PATH'])

    env.Alias('egg_info', egg_info)

    metadata = env.Command(env['DIST_INFO_PATH'].File('METADATA'), 
                           'pyproject.toml', metadata_builder)

    pkg_info = env.Command('PKG-INFO', egg_info_targets(env)[0].get_path(),
                           Copy('$TARGET', '$SOURCE'))  # TARGET and SOURCE are ''?

    wheel_filename = '-'.join((env['PACKAGE_NAME_SAFE'], env['PACKAGE_VERSION'], env['WHEEL_TAG'])) + '.whl'
    wheel_target_dir = env.Dir(env['WHEEL_BASE'])
    whl = env.Zip(target=env.Dir(wheel_target_dir).File(wheel_filename),
                  source=env['WHEEL_PATH'], ZIPROOT=env['WHEEL_PATH'])

    env.Alias('bdist_wheel', whl)

    env.AddPostAction(whl, Action(add_manifest))

    env.Clean(whl, env['WHEEL_PATH'])
    
    env.AddMethod(Whl)

    return
