#!/usr/bin/env python
# Pull arguments out of setup.py by monkeypatching setuptools.
# Run in a directory with setup.py to get a starter pyproject.toml and SConstruct
# Daniel Holth <dholth@fastmail.fm>, 2016

from __future__ import print_function, absolute_import

import runpy
from collections import OrderedDict
import setuptools, distutils.core
import sys, os, codecs, errno
import pytoml

import pkgutil

sconstruct_template = pkgutil.get_data("enscons", "SConstruct.in").decode("utf-8")


def find_src_root(metadata):
    """
    Determine source root from src_root or package_dir key.
    Replace package_dir in metadata with src_root.
    Only understands a single root.
    """
    src_root = ""  # instead of '.'
    if "package_dir" in metadata:
        try:
            src_root = metadata["package_dir"][""]
            del metadata["package_dir"]
        except KeyError:
            raise ValueError('Need package_dir mapping "" to a single directory')
    elif "src_root" in metadata:
        src_root = metadata["src_root"]
    metadata["src_root"] = src_root or ""
    return src_root


def _repr(value):
    """repr() without prefix"""
    return repr(value).strip("u")


def gen_sconstruct(metadata):
    """
    Build a starter SConstruct from pyproject metadata.

    Call find_src_root first to try to find metadata['src_root']
    """
    src_root = metadata["src_root"]

    # Include all Python files in py_modules or packages
    py_source = []
    for module in metadata.get("py_modules", []):
        module_path = os.path.join(src_root, module + ".py")
        py_source.append("[" + _repr(module_path) + "]")
    for package in metadata.get("packages", []):
        package_path = os.path.join(src_root, package.replace(".", os.sep), "*.py")
        py_source.append("Glob(" + _repr(package_path).strip("u") + ")")
    py_source = " + ".join(py_source)

    if not py_source:
        py_source = "[]"
        sys.stderr.write("No Python sources?\n")

    return sconstruct_template.format(py_source=py_source, src_root=_repr(src_root))


def write_no_clobber(filename, contents):
    """
    Write to new file `filename` as utf-8 encoded `contents`.
    Warn if existing file is the same as contents or different than contents.
    """
    try:
        with codecs.open(filename, "r", encoding="utf-8") as existing:
            existing_contents = existing.read()
            if existing_contents != contents:
                sys.stderr.write("Not overwriting existing file %s\n" % filename)
            else:
                sys.stderr.write("Existing file %s is up to date\n" % filename)
    except (OSError, IOError) as e:
        if not e.errno == errno.ENOENT:
            raise
        with codecs.open(filename, "w", encoding="utf-8") as f:
            f.write(contents)
            sys.stderr.write("Wrote %s\n" % filename)


def main():
    def setup_(**kw):
        setup_.arguments = kw

    setuptools.setup = setup_
    distutils.core.setup = setup_

    sys.path[0:0] = "."

    runpy.run_module("setup", run_name="__main__")

    # Convert the keys that enscons uses and a few more that are serializable.
    key_order = [
        "name",
        "version",
        "description",
        "classifiers",
        "keywords",
        "author",
        "author_email",
        "maintainer",
        "maintainer_email",
        "url",
        "license",
        "install_requires",
        "extras_require",
        "tests_require",
        "entry_points",
        "long_description",
        "py_modules",
        "packages",
        "package_dir",
    ]

    ordered_arguments = OrderedDict()
    for key in key_order:
        if key in setup_.arguments:
            ordered_arguments[key] = setup_.arguments.pop(key)

    if isinstance(ordered_arguments.get("keywords"), str):
        ordered_arguments["keywords"] = ordered_arguments["keywords"].split()

    if isinstance(ordered_arguments.get("install_requires"), str):
        ordered_arguments["install_requires"] = [ordered_arguments["install_requires"]]

    if isinstance(ordered_arguments.get("py_modules"), str):
        ordered_arguments["py_modules"] = [ordered_arguments["py_modules"]]

    find_src_root(ordered_arguments)

    if "long_description" in ordered_arguments:
        sys.stderr.write("Consider replacing long_description with description_file\n")

    pyproject = pytoml.dumps(
        OrderedDict(
            [
                ["project", ordered_arguments],
                [
                    "build-system",
                    {
                        "requires": ["pytoml>=0.1", "enscons"],
                        "build-backend": "enscons.api",
                    },
                ],
            ]
        ),
        sort_keys=False,
    )

    write_no_clobber("pyproject.toml", pyproject)

    sconstruct = gen_sconstruct(ordered_arguments)
    write_no_clobber("SConstruct", sconstruct)


if __name__ == "__main__":
    main()
