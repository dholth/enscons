"""
This module provides helper functions for packaging python code into wheels using enscons as a build backend.

A basic pure-python SConstruct may look like the following:

# SConstruct start

    import enscons
    import enscons.helpers
    import os

    env, version_file = enscons.helpers.prolog(None, enscons.get_universal_tag())
    package_source = [node for package in env["PACKAGE_METADATA"]["packages"]
                           for node in enscons.helpers.recursiveGlob(package)]

    # add other files (e.g. json configurations) to the package_source list as needed, you can use
    # enscons.helpers.recursiveGlob for this as well

    lib = env.Whl(env["WHEEL_TARGET"], package_source, root=".")
    lic_files = [x for x in os.listdir() if x.lower().startswith("license") or x.lower().startswith("notice")]
    lib += env.Install(env["DIST_INFO_PATH"], lic_files)

    enscons.helpers.epilog(env, lib, lic_files + version_file)

# SConstruct end

If you want to distribute shared objects, dll's or other binary code, you can use this template

# SConstruct start

    import enscons
    improt enscons.helpers
    import os

    env, version_file = enscons.helpers.prolog(None, enscons.get_universal_tag())
    package_source = [node for package in env["PACKAGE_METADATA"]["packages"] 
                           for node in enscons.helpers.recursiveGlob(package)]

    # add other files (e.g. json configurations) to the package_source list as needed, you can use 
    # enscons.helpers.recursiveGlob for this as well

    lib = env.Whl(env["WHEEL_TARGET"], package_source, root=".")
    lic_files = [x for x in os.listdir() if x.lower().startswith("license") or x.lower().startswith("notice")]
    lib += env.Install(env["DIST_INFO_PATH"], lic_files)

    if not "editable" in COMMAND_LINE_TARGETS:
        # assume we only have one package
        env["PACKAGE_NAME"] = env["PACKAGE_METADATA"]["packages"][0]
        # for each binary source, add the source to the wheel like this
        lib += env.Install("$WHEEL_PATH/$PACKAGE_NAME/<subdirectory>", binary_source)

    enscons.helpers.epilog(env, lib, lic_files + version_file)

# SConstruct end

If you want enable pyarmor, you can use this template:

# SConstruct start

    import enscons
    import enscons.helpers
    import os

    env, version_file = enscons.prolog(None, enscons.get_binary_tag())
    py_files = [node for package in env["PACKAGE_METADATA"]["packages"] 
                     for node in enscons.helpers.recursiveGlob(package)]

    lib = env.Whl(env["WHEEL_TARGET"], [], root=".")
    pyarmored = enscons.helpers.pyarmor(py_files, env)

    package_source = (pyfiles if pyarmored is None else [])
    # add other files (e.g. json configurations) to the package_source list as needed, you can use 
    # enscons.helpers.recursiveGlob for this as well

    lib += env.Whl(env["WHEEL_TARGET"], package_source, root=".")
    lic_files = [x for x in os.listdir() if x.lower().startswith("license") or x.lower().startswith("notice")]
    lib += env.Install(env["DIST_INFO_PATH"], lic_files)
    if pyarmored is not None:
        lib += pyarmored

    enscons.helpers.epilog(env, lib, lic_files + version_file)

# SConstruct end

"""

import os
from pathlib import Path
import shutil
import sys
import tempfile
import traceback
import enscons
import pytoml as toml
from SCons.Script import *

def recursiveGlob(root, pattern="*.py", ignoreNames=None, expectFile=None):
    """
    Helper function for recursively globbing package source files
    
    :param root: base directory to search
    :param pattern: file name pattern (default: *.py)
    :param ignoreNames: directory names to ignore (default: ["__pycache__"])
    :param expectFile: directories without at least one of the given files are ignored (default: ["__init__.py"])
    :return: a list of SCons file nodes matching the rules
    """
    ignoreNames = ["__pycache__"] if ignoreNames is None else ignoreNames
    expectFile = ["__init__.py"] if expectFile is None else [expectFile] if isinstance(expectFile, str) else expectFile
    matches = []
    res = Glob(os.path.join(root, pattern))
    for oswroot, oswdirnames, _ in os.walk(root):
        for oswdirname in oswdirnames:
            if oswdirname in ignoreNames:
                print("[%s]: Ignoring %s (directory name is ignored)." % (pattern, os.path.join(oswroot, oswdirname)))
                continue
            found = any([os.path.isfile(os.path.join(oswroot, oswdirname, fn)) for fn in expectFile])
            if (not found) and len(expectFile) > 0:
                print("[%s]: Ignoring %s (expected files %s not found)." % (pattern, os.path.join(oswroot, oswdirname), expectFile))
                continue
            res.extend(Glob(os.path.join(oswroot, oswdirname, pattern)))
    return res

def prolog(os_environ_version_key, wheel_tag, is_binary=None, py_project_toml="pyproject.toml"):
    """
    Function supporting an enscons build to remove some boilerplate copy/paste stuff. 
    Use env["PACKAGE_METADATA"] to access the toml metadata.
    Use env["WHEEL_TARGET"] to access the target ("purelib" or "platlib")
    
    :param os_environ_version_key: the name of the environment variable containing the version number (might be None)
    :param wheel_tag: the tag for the wheel (you can use enscons.get_abi3_tag() for binary wheels and enscons.get_universal_tag() for pure python wheels)
    :param py_project_toml: the name of the pyproject.toml file
    :return: scons environment, version_file SCons node
    """
    if is_binary is None:
        is_binary = "-none-any" not in wheel_tag
    
    if Dir("#build").exists():
        # these directories might cause troubles -> remove them before doing anything else
        print("Removing left-over build directory")
        shutil.rmtree(Dir("#build").abspath, ignore_errors=True)
    
    metadata = dict(toml.load(open("pyproject.toml")))["project"]
    if os.path.isfile("VERSION.txt"):
        metadata["version"] = open("VERSION.txt").read().strip()
        version_file = ["VERSION.txt"]
    else:
        default_version = "99.99.99"
        metadata["version"] = os.environ.get(os_environ_version_key, default_version) if os_environ_version_key is not None else default_version
        version_file = None

    env = Environment(
        tools=["default", "packaging", "textfile", enscons.generate],
        PACKAGE_METADATA=metadata,
        WHEEL_TAG=wheel_tag,
        ENV=os.environ.copy(),
        WHEEL_TARGET="platlib" if is_binary else "purelib"       
    )

    if version_file is None:
        # version files will be put into the source distribution
        version_file = env.Textfile("VERSION.txt", metadata["version"])
    
    return env, version_file

def epilog(env, lib, additional_source_files):
    """
    Function supporting an enscons build to remove some boilerplate copy/paste stuff.

    :param env: The SCons environment to be used
    :param lib: The lib targets as a source to env.Wheel
    :param additional_source_files: additional files to be added to sdist (e.g. LICENSE, NOTICE, ...)
    """
    whl = env.WhlFile(lib)

    # Add automatic source files, plus any other needed files.
    sdist_source = FindSourceFiles() + ["PKG-INFO", "setup.py", "pyproject.toml"] + additional_source_files
    sdist = env.SDist(source=sdist_source)

    env.NoClean(sdist)
    env.Alias("sdist", sdist)

    develop = env.Command("#DEVELOP", enscons.egg_info_targets(env), enscons.develop)
    env.Alias("develop", develop)

    # needed for pep517 / enscons.api to work
    env.Default(whl, sdist)

def pyarmor_enabled():
    pyarmor_platform = ARGUMENTS.get("pyarmor_platform", None)
    pyarmor_license = ARGUMENTS.get("pyarmor_license", None)
    pyarmor_cmd = ARGUMENTS.get("pyarmor_cmd", None)
    pyarmor_flags = ARGUMENTS.get("pyarmor_flags", None)
    if pyarmor_platform is not None or pyarmor_license is not None or pyarmor_cmd is not None or pyarmor_flags is not None:
        return True
    return False

def pyarmor(py_files, env):
    """
    Function for supporting pyarmor obfuscation. The obfuscation is controlled via the SCons arguments 
    pyarmor_platform, pyarmor_license, pyarmor_cmd, pyarmor_flags. If at least one of these arguments is
    present, then pyarmor is enabled.
    
    Note: This is a pretty basic usage of pyarmor. More advanced usages with restrict may probably require the
    usage of pyarmor projects (https://pyarmor.readthedocs.io/en/v7.7/project.html), which is out of scope here.
    
    :param py_files: the python files of the project (potentially obfuscated)
    :param env: the scons environment where env.Whl already has been executed at least once.
    :return: the pyarmored files or None if pyarmor is not configured
    """
    pyarmor_platform = ARGUMENTS.get("pyarmor_platform", None)
    pyarmor_license = ARGUMENTS.get("pyarmor_license", None)
    pyarmor_cmd = ARGUMENTS.get("pyarmor_cmd", None)
    pyarmor_flags = ARGUMENTS.get("pyarmor_flags", None)
    pyarmored = None
    if pyarmor_platform is not None or pyarmor_license is not None or pyarmor_cmd is not None or pyarmor_flags is not None:
        if pyarmor_cmd is None:
            pyarmor_cmd = "%s -m pyarmor.pyarmor" % sys.executable
        pyarmor_args = "" if pyarmor_flags is None else pyarmor_flags
        pyarmor_license = [pyarmor_license] if pyarmor_license is not None else []
        #reglic = env.Command(["non_existing_dummy_file"], [pyarmor_license], "%s register ${SOURCES[0]}" % pyarmor_cmd)
        if pyarmor_platform is not None:
            pyarmor_args += " --platform=%s" % pyarmor_platform

        sources = []
        targets = []
        for f in py_files:
            sources.append(f)
            targets.append(env["WHEEL_PATH"].File(str(f)))
        targets.append(env["WHEEL_PATH"].Dir("ifm_o3r_cmf").Dir("pytransform"))
        
        def pyarmorify(target, source, env):
            try:
                with tempfile.TemporaryDirectory() as tmpdir:
                    first_source = None
                    for i, tgtfile in enumerate(target[:-1]):
                        srcfile = str(source[i])
                        tgtdir = Path(tmpdir) / str(source[i].dir)
                        tgtdir.mkdir(parents=True, exist_ok=True)
                        shutil.copy(srcfile, tgtdir)
                        if i == 0:
                            first_source = tgtdir / Path(srcfile).name
                    if len(source) == len(target):
                        print("%s register %s" % (pyarmor_cmd, source[-1]))
                        if env.Execute("%s register %s" % (pyarmor_cmd, source[-1])):
                            raise RuntimeError("pyarmor register returned error")
                    elif len(source)+1 != len(target):
                        raise RuntimeError("Unexpected list lengths")
                    print("%s obfuscate %s --recursive --output $WHEEL_PATH/${PACKAGE_METADATA['packages'][0]} %s" % (pyarmor_cmd, pyarmor_args, first_source))
                    if env.Execute("%s obfuscate %s --recursive --output $WHEEL_PATH/${PACKAGE_METADATA['packages'][0]} %s" % (pyarmor_cmd, pyarmor_args, first_source)):
                        raise RuntimeError("pyarmor obfuscate returned error")
            except Exception as e:
                traceback.print_exc()
                return 1
            return 0
        
        # we are using whole package mode here
        pyarmored = env.Command(targets, sources + pyarmor_license, 
                                pyarmorify)
        
    return pyarmored
    
