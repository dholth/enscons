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

from __future__ import unicode_literals, print_function

import os
import sys
import time

# avoid timestamps before 1980 to be friendly to .zip
SOURCE_EPOCH_TGZ = 499162800
SOURCE_EPOCH_ZIP = 499162860

# SCons installs itself in an odd path, under an empty scons/ directory
prefs = []

try:
    import SCons.Script
except ImportError:
    if "SCons" in sys.modules:
        del sys.modules["SCons"]  # or it won't try again
    try:
        # empty scons directory (lowercase) is also a Python 3 namespace package
        import scons

        prefs.extend(scons.__path__)
    except (ImportError, AttributeError):
        # python 2 / pkg_resources method
        try:
            import pkg_resources
        except ImportError:
            pass
        else:
            try:
                d = pkg_resources.get_distribution("scons")
            except pkg_resources.DistributionNotFound:
                pass
            else:
                prefs.append(os.path.join(d.location, "scons"))

sys.path = prefs + sys.path

import SCons.Script

from SCons.Script import Copy, Action, FindInstalledFiles, GetOption, AddOption

from distutils import sysconfig
from collections import defaultdict

from .util import safe_name, to_filename, generate_requirements

import codecs
import distutils.ccompiler, distutils.sysconfig, distutils.unixccompiler
import os.path
import SCons.Node.FS


def get_binary_tag():
    """
    Return most-specific binary extension wheel tag 'interpreter-abi-arch'
    """
    from packaging import tags

    return str(next(tag for tag in tags.sys_tags() if not "manylinux" in tag.platform))


def get_universal_tag():
    """
    Return 'py2.py3-none-any'
    """
    return "py2.py3-none-any"


def get_abi3_tag():
    """
    Return first abi3 tag, or the first binary tag if abi3 is not supported.
    """
    from packaging import tags

    try:
        return str(
            next(
                tag
                for tag in tags.sys_tags()
                if "abi3" in tag.abi and "manylinux" not in tag.platform
            )
        )
    except StopIteration:
        return get_binary_tag()


def normalize_package(name):
    # XXX encourage project names to start out 'safe'
    return to_filename(safe_name(name))


def egg_info_targets(env):
    """
    Write the minimum .egg-info for pip. Full metadata will go into wheel's .dist-info
    """
    return [
        env.fs.Dir(env["EGG_INFO_PATH"]).File(name)
        for name in ["PKG-INFO", "requires.txt", "entry_points.txt"]
    ]


def develop(env, target=None, source=None):
    """
    Add `scons develop` target to your SConstruct with

    develop = env.Command("#DEVELOP", enscons.egg_info_targets(env), enscons.develop)
    env.Alias("develop", develop)
    """
    import enscons.setup

    enscons_defaults(env)
    enscons.setup.develop(env["EGG_INFO_PREFIX"] or ".")


def requires_txt_builder(target, source, env):
    """
    Build requires.txt from PACKAGE_METADATA variable.
    """
    metadata = env["PACKAGE_METADATA"]
    full_requires = {}
    full_requires.update(metadata.get("extras_require", {}))
    full_requires.update(metadata.get("optional-dependencies", {}))
    # install_requires is equivalent to extras_require[""][...]
    if "install_requires" in metadata:
        full_requires[""] = metadata["install_requires"]
    if "dependencies" in metadata:
        full_requires[""] = metadata["dependencies"]
    with codecs.open(target[0].get_path(), mode="w", encoding="utf-8") as f:
        for group, dependencies in sorted(full_requires.items()):
            if group:
                f.write("\n[%s]\n" % group)
            for dep in dependencies:
                f.write("%s\n" % dep)


def entry_points_builder(target, source, env):
    """
    Build entry_points.txt from PACKAGE_METADATA variable.
    """
    metadata = env["PACKAGE_METADATA"]
    entry_points = {}
    if "entry_points" in metadata:
        entry_points.update(metadata["entry_points"])
    if "scripts" in metadata:
        entry_points["console_scripts"] = metadata["scripts"]
    if "gui-scripts" in metadata:
        entry_points["gui_scripts"] = metadata["gui-scripts"]
    with codecs.open(target[0].get_path(), mode="w", encoding="utf-8") as f:
        for group, items in sorted(entry_points.items()):
            f.write("[%s]\n" % group)
            if isinstance(items, list):
                # Non-PEP 621 extension: entry_point tables as lists of strings
                for item in items:
                    f.write("%s\n" % item)
            else:
                for key, value in sorted(items.items()):
                    f.write("%s = %s\n" % (key, value))


def egg_info_builder(target, source, env):
    """
    Minimum egg_info. To be used only by pip to get dependencies.
    """
    metadata = env["PACKAGE_METADATA"]
    for dnode in env.arg2nodes(target):
        if dnode.name == "PKG-INFO":
            with open(dnode.get_path(), "w") as f:
                f.write("Metadata-Version: 1.1\n")
                f.write("Name: %s\n" % env["PACKAGE_NAME"])
                f.write("Version: %s\n" % env["PACKAGE_VERSION"])
        elif dnode.name == "requires.txt":
            requires_txt_builder([dnode], source, env)
        elif dnode.name == "entry_points.txt":
            entry_points_builder([dnode], source, env)


try:
    basestring
except NameError:
    basestring = str


def _is_string(obj):
    # Python 2 compatibility.
    return isinstance(obj, basestring)


def _read_file(filename, encoding="utf-8"):
    with codecs.open(filename, mode="r", encoding=encoding) as f:
        return f.read()


def _write_header(f, name, value):
    lines = value.splitlines() or [""]
    f.write("%s: %s\n" % (name, lines[0]))
    for line in lines[1:]:
        f.write("  %s\n" % line)


def _write_contacts(f, header_name, header_email, contacts):
    if len(contacts) == 1:
        if "name" in contacts[0]:
            _write_header(f, header_name, contacts[0]["name"])
        if "email" in contacts[0]:
            _write_header(f, header_email, contacts[0]["email"])
    else:
        value = ", ".join(
            contact["email"]
            if "name" not in contact
            else contact["name"]
            if "email" not in contact
            else "%(name)s <%(email)s>" % contact
            for contact in contacts
        )
        emails = any("email" in contact for contact in contacts)
        _write_header(f, header_email if emails else header_name, value)


def metadata_source(env):
    metadata = env["PACKAGE_METADATA"]
    source = ["pyproject.toml"]
    # The logic here duplicates parts of metadata_builder().
    # Maybe the two should be unified.
    if "license" in metadata:
        if not _is_string(metadata["license"]):
            if not ("text" in metadata["license"]):
                source.append(metadata["license"]["file"])
    if "readme" in metadata:
        if _is_string(metadata["readme"]):
            source.append(metadata["readme"])
        else:
            if "file" in metadata["readme"]:
                source.append(metadata["readme"]["file"])
    elif "description_file" in metadata:
        source.append(metadata["description_file"])
    return source


def metadata_builder(target, source, env):
    metadata = env["PACKAGE_METADATA"]
    with codecs.open(target[0].get_path(), mode="w", encoding="utf-8") as f:
        f.write("Metadata-Version: 2.1\n")
        # Key meanings in accordance with PEP 621, with minor
        # extensions for backward compatibility. The "dynamic"
        # key is not implemented.
        f.write("Name: %s\n" % metadata["name"])
        f.write("Version: %s\n" % metadata["version"])
        if "description" in metadata:
            _write_header(f, "Summary", metadata["description"])
        if "requires-python" in metadata:
            _write_header(f, "Requires-Python", metadata["requires-python"])
        if "license" in metadata:
            _write_header(
                f,
                "License",
                metadata["license"]
                if _is_string(metadata["license"])
                else metadata["license"]["text"]
                if "text" in metadata["license"]
                else _read_file(metadata["license"]["file"]),
            )
        if "authors" in metadata:
            _write_contacts(f, "Author", "Author-email", metadata["authors"])
        else:
            # Non-PEP 621 keys.
            if "author" in metadata:
                _write_header(f, "Author", metadata["author"])
            if "author_email" in metadata:
                _write_header(f, "Author-email", metadata["author_email"])
        if "maintainers" in metadata:
            _write_contacts(
                f, "Maintainer", "Maintainer-email", metadata["maintainers"]
            )
        if "keywords" in metadata:
            _write_header(
                f,
                "Keywords",
                metadata["keywords"]
                if _is_string(metadata["keywords"])
                else ",".join(metadata["keywords"]),
            )
        for classifier in metadata.get("classifiers", []):
            _write_header(f, "Classifier", classifier)
        if "url" in metadata:
            # This is not present in PEP 621.
            _write_header(f, "Home-Page", metadata["url"])
        for label, url in metadata.get("urls", {}).items():
            _write_header(f, "Project-URL", "%s, %s" % (label, url))
        if "platform" in metadata:
            # Backward compatibility only.
            _write_header(f, "Platform", metadata["platform"])
        full_requires = {}
        full_requires.update(metadata.get("extras_require", {}))
        full_requires.update(metadata.get("optional-dependencies", {}))
        # install_requires is equivalent to extras_require[""][...]
        if "install_requires" in metadata:
            full_requires[""] = metadata["install_requires"]
        if "dependencies" in metadata:
            full_requires[""] = metadata["dependencies"]
        for requirement in generate_requirements(full_requires):
            f.write("%s: %s\n" % requirement)
        if "readme" in metadata:
            if _is_string(metadata["readme"]):
                filename = metadata["readme"]
                contenttype = None
                content = _read_file(filename)
            else:
                if "file" in metadata["readme"]:
                    filename = metadata["readme"]["file"]
                    contenttype = metadata["readme"].get("content-type", None)
                    encoding = metadata["readme"].get("encoding", "utf-8")
                    content = _read_file(filename, encoding=encoding)
                else:
                    filename = None
                    contenttype = metadata["readme"].get("content-type", None)
                    content = metadata["readme"]["text"]
            if contenttype is None and filename:
                lowername = filename.lower()
                contenttype = (
                    "text/x-rst"
                    if lowername.endswith(".rst")
                    else "text/markdown"
                    if lowername.endswith(".md")
                    else "text/plain"
                    if lowername.endswith(".txt")
                    else None
                )
            if contenttype:
                _write_header(f, "Description-Content-Type", contenttype)
            f.write("\n\n")
            f.write(content)
        elif "description_file" in metadata:
            # Backward compatibility.
            f.write("\n\n")
            f.write(_read_file(metadata["description_file"]))


import base64


def urlsafe_b64encode(data):
    """urlsafe_b64encode without padding"""
    return base64.urlsafe_b64encode(data).rstrip(b"=")


def add_editable(target, source, env):
    """
    Add the editable stub modules to a zip file.
    """
    import zipfile
    import editables
    import os.path

    project_name = env["PACKAGE_METADATA"].get("name")
    src_root = os.path.abspath(env["PACKAGE_METADATA"].get("src_root", ""))

    project = editables.EditableProject(project_name, src_root)
    project.add_to_path(src_root)

    archive = zipfile.ZipFile(
        target[0].get_path(), "a", compression=zipfile.ZIP_DEFLATED
    )
    lines = []
    for f, data in project.files():
        archive.writestr(zipfile.ZipInfo(f, time.gmtime(SOURCE_EPOCH_ZIP)[:6]), data)
    archive.close()


def add_manifest(target, source, env):
    """
    Add the wheel manifest.
    """
    import hashlib
    import zipfile

    archive = zipfile.ZipFile(
        target[0].get_path(), "a", compression=zipfile.ZIP_DEFLATED
    )
    lines = []
    for f in archive.namelist():
        data = archive.read(f)
        size = len(data)
        digest = hashlib.sha256(data).digest()
        digest = "sha256=" + (urlsafe_b64encode(digest).decode("ascii"))
        lines.append("%s,%s,%s" % (f.replace(",", ",,"), digest, size))

    record_path = env["DIST_INFO_PATH"].get_path(dir=env["WHEEL_PATH"]) + "/RECORD"
    lines.append(record_path + ",,")
    RECORD = "\n".join(lines)
    archive.writestr(
        zipfile.ZipInfo(record_path, time.gmtime(SOURCE_EPOCH_ZIP)[:6]), RECORD
    )
    archive.close()


def wheelmeta_builder(target, source, env):
    with open(target[0].get_path(), "w") as f:
        f.write(
            """Wheel-Version: 1.0
Generator: enscons (0.0.1)
Root-Is-Purelib: %s
Tag: %s
"""
            % (str(env["ROOT_IS_PURELIB"]).lower(), env["WHEEL_TAG"])
        )


def wheel_metadata(env):
    """Build the wheel metadata."""
    metadata = env.Command(
        env["DIST_INFO_PATH"].File("METADATA"), metadata_source(env), metadata_builder
    )
    wheelfile = env.Command(
        env["DIST_INFO_PATH"].File("WHEEL"), "pyproject.toml", wheelmeta_builder
    )
    entry_points = env.Command(
        env["DIST_INFO_PATH"].File("entry_points.txt"),
        "pyproject.toml",
        entry_points_builder,
    )
    return [metadata, wheelfile, entry_points]


def init_wheel(env):
    """
    Create a wheel and its metadata using Environment env.
    """
    env["PACKAGE_NAMEVER"] = "-".join(
        (env["PACKAGE_NAME_SAFE"], env["PACKAGE_VERSION"])
    )

    wheel_filename = "-".join((env["PACKAGE_NAMEVER"], env["WHEEL_TAG"])) + ".whl"
    wheel_target_dir = env.Dir(env["WHEEL_DIR"])

    # initial # here in path means its relative to top-level sconstruct
    env["WHEEL_PATH"] = env.get("WHEEL_PATH", env.Dir("#build/wheel/"))
    env["DIST_INFO_NAME"] = env["PACKAGE_NAMEVER"] + ".dist-info"

    env["DIST_INFO_PATH"] = env["WHEEL_PATH"].Dir(
        env["PACKAGE_NAME_SAFE"] + "-" + env["PACKAGE_VERSION"] + ".dist-info"
    )
    env["WHEEL_DATA_PATH"] = env["WHEEL_PATH"].Dir(
        env["PACKAGE_NAME_SAFE"] + "-" + env["PACKAGE_VERSION"] + ".data"
    )

    # used by prepare_metadata_for_build_wheel
    dist_info = env.Install(env.Dir(env["WHEEL_DIR"]), env["DIST_INFO_PATH"])
    env.Alias("dist_info", dist_info)

    env["WHEEL_FILE"] = env.Dir(wheel_target_dir).File(wheel_filename)

    # Write WHEEL and METADATA
    targets = wheel_metadata(env)

    # experimental PEP517-style editable
    # with filename that won't collide with our real wheel (SCons wouldn't like that)
    editable_filename = (
        "-".join((env["PACKAGE_NAMEVER"], "ed." + env["WHEEL_TAG"])) + ".whl"
    )
    editable = env.Zip(
        target=env.Dir(env["WHEEL_DIR"]).File(editable_filename),
        source=env["DIST_INFO_PATH"],
        ZIPROOT=env["WHEEL_PATH"],
    )
    env.Alias("editable", editable)
    env.NoClean(editable)
    env.AddPostAction(editable, Action(add_editable))
    env.AddPostAction(editable, Action(add_manifest))

    editable_dist_info = env.Dir("#build/editable/${PACKAGE_NAMEVER}.dist-info")
    # editable may need an extra dependency, so it gets its own dist-info directory.
    env.Command(editable_dist_info, env["DIST_INFO_PATH"], Copy("$TARGET", "$SOURCE"))

    metadata2 = env.Command(
        editable_dist_info.File("METADATA"), metadata_source(env), metadata_builder
    )

    return targets


def Whl(env, category, source, root=None):
    """
    Copy wheel members into their archive locations.
    category: 'purelib', 'platlib', 'headers', 'data' etc.
    source: files belonging to category
    root: relative to root directory i.e. '.', 'src'
    """
    enscons_defaults(env)

    # Create target the first time this is called
    wheelmeta = []
    try:
        env["WHEEL_FILE"]
    except KeyError:
        wheelmeta = init_wheel(env)

    targets = []
    in_root = ("platlib", "purelib")[env["ROOT_IS_PURELIB"]]
    if category == in_root:
        target_dir = env["WHEEL_PATH"].get_path()
    else:
        target_dir = env["WHEEL_DATA_PATH"].Dir(category).get_path()
    for node in env.arg2nodes(source):
        relpath = os.path.relpath(node.get_path(), root or "")
        args = (os.path.join(target_dir, relpath), node)
        targets.append(env.InstallAs(*args))

    return targets + wheelmeta


def _patch_source_epoch():
    """
    SCons ZIP doesn't accept this as a parameter yet.
    """
    if hasattr(_patch_source_epoch, "_once"):
        return
    _patch_source_epoch._once = True

    import zipfile

    try:
        _from_file = zipfile.ZipInfo.from_file
    except AttributeError:  # Python 2?
        return

    def from_file(filename, arcname=None, **kwargs):
        zinfo = _from_file(filename, arcname, **kwargs)
        zinfo.date_time = time.gmtime(SOURCE_EPOCH_ZIP)[0:6]
        return zinfo

    zipfile.ZipInfo.from_file = from_file


def WhlFile(env, target=None, source=None):
    """
    Archive wheel members collected from Whl(...)
    """
    enscons_defaults(env)

    # positional arguments for older enscons
    if target and not source:
        source = target
        target = None

    _patch_source_epoch()

    whl = env.Zip(
        target=target or env.get("WHEEL_FILE"), source=source, ZIPROOT=env["WHEEL_PATH"]
    )

    env.NoClean(whl)
    env.Alias("bdist_wheel", whl)
    env.AddPostAction(whl, Action(add_manifest))
    env.Clean(whl, env["WHEEL_PATH"])

    return whl


def SDist(env, target=None, source=None):
    """
    Call env.Package() with sdist filename inferred from
    env['PACKAGE_METADATA'] etc.
    """
    enscons_defaults(env)

    egg_info = env.Command(egg_info_targets(env), "pyproject.toml", egg_info_builder)
    env.Clean(egg_info, env["EGG_INFO_PATH"])
    env.Alias("egg_info", egg_info)

    pkg_info = env.Command("PKG-INFO", metadata_source(env), metadata_builder)

    # also the root directory name inside the archive
    target_prefix = "-".join((env["PACKAGE_NAME"], env["PACKAGE_VERSION"]))
    if not target:
        target = [os.path.join(env["DIST_BASE"], target_prefix)]

    source = sorted(env.arg2nodes(source, env.fs.Entry))

    sdist = env.PyTar(
        target=target,
        source=source,
        TARPREFIX=target_prefix,
        TARSUFFIX=".tar.gz",
        TARUID=0,
        TARGID=0,
        TARMTIME=SOURCE_EPOCH_TGZ,
    )
    env.Alias("sdist", sdist)
    return sdist


def enscons_defaults(env):
    """
    To avoid setting these in generate().
    """
    once_key = "_ENSCONS_DEFAULTS"
    if once_key in env:
        return
    env[once_key] = True

    try:
        env["ROOT_IS_PURELIB"]
    except KeyError:
        env["ROOT_IS_PURELIB"] = env["WHEEL_TAG"].endswith("none-any")

    env["EGG_INFO_PREFIX"] = GetOption("egg_base")  # pip wants this in a target dir
    env["WHEEL_DIR"] = GetOption("wheel_dir") or "dist"  # target directory for wheel
    env["DIST_BASE"] = GetOption("dist_dir") or "dist"

    env["PACKAGE_NAME"] = env["PACKAGE_METADATA"]["name"]
    env["PACKAGE_NAME_SAFE"] = normalize_package(env["PACKAGE_NAME"])
    env["PACKAGE_VERSION"] = env["PACKAGE_METADATA"]["version"]

    # place egg_info in src_root if defined
    if not env["EGG_INFO_PREFIX"] and env["PACKAGE_METADATA"].get("src_root"):
        env["EGG_INFO_PREFIX"] = env["PACKAGE_METADATA"]["src_root"]

    # Development .egg-info has no version number. Needs to have
    # underscore _ and not hyphen -
    env["EGG_INFO_PATH"] = env["PACKAGE_NAME_SAFE"] + ".egg-info"
    if env["EGG_INFO_PREFIX"]:
        env["EGG_INFO_PATH"] = env.Dir(env["EGG_INFO_PREFIX"]).Dir(env["EGG_INFO_PATH"])


def generate(env):
    """
    Set up enscons in Environment env
    """

    # pure-Python tar
    from . import pytar

    pytar.generate(env)

    if not hasattr(generate, "once"):
        AddOption(
            "--egg-base",
            dest="egg_base",
            type="string",
            nargs=1,
            action="store",
            metavar="DIR",
            help="egg-info target directory",
        )

        AddOption(
            "--wheel-dir",
            dest="wheel_dir",
            type="string",
            nargs=1,
            action="store",
            metavar="DIR",
            help="wheel target directory",
        )

        AddOption(
            "--dist-dir",
            dest="dist_dir",
            type="string",
            nargs=1,
            action="store",
            metavar="DIR",
            help="sdist target directory",
        )

        generate.once = True

    env.AddMethod(Whl)
    env.AddMethod(WhlFile)
    env.AddMethod(SDist)


def exists(env):  # only used if enscons is found on SCons search path
    return True
