Enscons Documentation
=====================

Enscons provides a set of Builders and utility functions for `SCons <https://scons.org>`_
to build Python distribution wheels. It provides a `PEP 517 <https://peps.python.org/pep-0517/>`_
build backend, compatible with popular build frontends such as Pip and
`Build <https://pypa-build.readthedocs.io/en/stable/>`_.

Project Layout
--------------
To get started, your project must have at least these two files in the project's top level
directory: a ``pyproject.toml`` and an ``SConstruct`` file.

pyproject.toml
--------------
At a minimum, your pyproject.toml file must contain the build-system requirements and
build-backend.

.. code-block:: toml

    [build-system]
    requires = ["enscons"]
    build-backend = "enscons.api"

This tells build frontends such as ``pip`` to build the package using Enscons. Add any other
*build-time* requirements to the requires list here. This should only be requirements needed
to build the wheel. Runtime dependencies should not be specified here.

It is recommended to add other static project metadata to a ``[project]`` section in this file
in accordance with `PEP 621 <https://peps.python.org/pep-0621/>`_.
Here's an example showing the essential items that Enscons knows about:

.. code-block:: toml

    [project]
    name = "distribution_name"
    description = "Project Description"
    version = "0.0.1"
    license = "MIT"
    authors = [
        {name = "Author Name", email = "authoremail@example.com"}
    ]
    readme = "README.md"
    requires-python: ">=3.8"
    dependencies = ["click", "requests"]
    keywords = ["keyword1", "keyword2"]
    classifiers = [
        "Programming Language :: Python :: 3",
    ]
    url = "https://example.com/myproject"

    # This specifies the root directory which will be added to the python path when
    # installing in editable mode (pip install -e)
    src_root = "."

    [project.scripts]
    my-script = "packagename.modulename:main"

    [project.optional-dependencies]
    more = ["sphinx"]

SConstruct
..........

This file defines how to build your package. It may be helpful to familiarize yourself with
SCons by reading the `SCons Crash Course <https://github.com/SCons/scons/wiki/SConsCrashCourse>`_
but here's a quick primer:

SCons is a build utility similar to ``make`` but which uses a Python script to declare targets
and the dependency graph. This script is named ``SConstruct`` but may also be called
``SConstruct.py`` or ``sconstruct.py`` which may be helpful to enable syntax highlighting
in your editor.

An SCons script's defines *Builders* which will declare how to build *targets*
from *sources*. Sources and targets are typically files or directories, and are collectively
known as *nodes*. The nodes then form a dependency graph with the builders as edges.

A basic SConstruct file for building a Python wheel consists of an ``Environment``, a ``Whl``
builder, a ``WhlFile`` builder, and an ``SDist`` builder.

Here's a simple and complete example. The following sections will go over each part in more detail.

.. code-block:: python

        import pytoml as  toml
        import enscons

        metadata = toml.load(open("pyproject.toml"))["project"]
        tag = "py3-none-any"

        env = Environment(
            tools=["default", "packaging", enscons.generate],
            PACKAGE_METADATA=metadata,
            WHEEL_TAG=tag,
        )

        py_sources = env.Glob("mypackage/*.py")

        purelib = env.Whl("purelib", py_sources)
        whl = env.WhlFile(purelib)
        sdist = env.SDist(env.FindSourceFiles() + ["PKG-INFO", "README.md"])

        # Sets the default target when scons is run on the command line with no target
        env.Default(whl, sdist)

Note that the ``Environment`` class is not imported. It is injected into the script's globals
by the SCons runtime.


Creating the Environment
........................
The SConstruct ``Environment`` object should be created as shown:

.. code-block:: python

        metadata = dict(toml.load(open("pyproject.toml")))["project"]
        tag = "py3-none-any"

        env = Environment(
            tools=["default", "packaging", enscons.generate],
            PACKAGE_METADATA=metadata,
            WHEEL_TAG=tag,
        )

The ``tools`` parameter defines which plugins are loaded into this environment. We'll want to
add the default and packaging tools provided by SCons, as well as the enscons tool, which loads
the enscons builders.

Additional keyword arguments set the Environment's *construction environment variables*. (this is
different than the system process's environment). Two variables are required:

The :py:data:`PACKAGE_METADATA` should typically come from the ``pyproject.toml`` file's
``[project]`` section as shown, but doesn't have to.
Most `PEP 621 <https://peps.python.org/pep-0621/>`_ items are accepted and incorporated into
the wheel's metadata.

The wheel tag should be set to the
`PEP 425 <https://peps.python.org/pep-0425/>`_,
compatibility tag of the wheel. See :py:data:`WHEEL_TAG` for more information.

More environment variables may be defined, and are described in the `Environment Variables`_
section.

Environment Builders
....................

.. py:function:: env.Whl(category, source, root=None)

    Copies wheel members into their archive locations.

    :param str category: "purelib", "platlib", "headers", "data", etc.
    :param source: files belonging to category
    :param root: relative to root directory, i.e. ".", "src"
    :returns: A list of file nodes for each file added

    This should be called at least once to add members into the wheel file. Typically, this
    would be called once to add all Python sources to the wheel. It may be called more
    than once to add additional sources to the wheel.

    For pure Python wheels, you'll typically want to use a :py:data:`WHEEL_TAG` ending in
    "none-any" in the environment, and set the ``category`` here to "purelib". Source
    files passed in will be copied into the root of the wheel.

    For wheels with a binary compiled or platform-specific component, you'll want to use "platlib"
    along with a platform-specific :py:data:`WHEEL_TAG`. Source files passed in will be
    copied into the root of the wheel.

    Any other category will add files into the corresponding subdirectory of the
    :py:data:`WHEEL_DATA_PATH` directory (e.g. ``projectname-0.0.1.data/category``)

    Returns a list of nodes for the files added to the wheel (both source files and metadata
    files). The returned nodes should later be passed in to :py:func:`env.WhlFile`
    as the list of sources.

    ``root`` determines the directory for which the sources are relative to. Source files are
    copied to the target directory along with all path components between ``root`` and the file
    itself.

.. py:function:: env.WhlFile([target=None, ]source=None)

    Build the wheel archive from the given sources. If a single positional parameter is
    given, it is taken to be the ``source`` parameter.

    :param source: A list of file nodes to add to the wheel archive. Typically this is a list
        of nodes as returned from :py:func:`env.Whl` (or the concatenated list from all calls)

    :param str target: The path to the wheel file being created. By default this is
        :py:data:`WHEEL_FILE`

    :returns: A file node for the resulting wheel file.


    Calling this also adds the build target "bdist_wheel".

.. py:function:: env.SDist(target=None, source=None)

    Creates a source distribution

    :param target: The path to the source distribution output
    :param source: A list of source files to include
    :returns: The source dist node

    n.b. Only explicitly named sources are added to the source distribution. To make
    this easier, the :py:func:`env.FindSourceFiles()` function is convenient starting point.
    It discovers all files that are sources to some other SCons build target.

    You will need to add explicitly add any other metadata files you want to include, such as
    ``PKG-INFO``, ``pyproject.toml``, ``SConstruct``, etc.
    (``PKG-INFO`` is automatically generated by enscons if named as a source)

    e.g.

    .. code-block:: python

        sdist = env.SDist(env.FindSourceFiles() + [
            "PKG-INFO", "README.md", "pyproject.toml", "SConstruct"
        ])

    Calling this also adds a build target named "sdist".

Environment Variables
---------------------

These variables are settable using kwargs to the ``Environment()`` constructor.

.. py:data:: PACKAGE_METADATA

    Package metadata used by the rest of the wheel building code. This is typically pulled from
    the "project" section of the ``pyproject.toml`` file as shown

    .. code-block:: python

        metadata = dict(toml.load(open("pyproject.toml")))["project"]

    This variable is required. Most `PEP 621 <https://peps.python.org/pep-0621/>`_ items are
    accepted and incorporated into the package's metadata.

.. py:data:: WHEEL_TAG

    This specifies the *compatibility tags* component of the python wheel filename and wheel
    metadata. It is a hyphen-delimited string specifying the the python version, abi, and
    platform tags. e.g. ``py3-none-none`` for pure python, or ``cp3-abi3-linux_x86_64`` for
    a wheel with binary compiled libraries for linux x86_64 and conforming to the abi3 binary
    interface.

    This variable is required.

    More information on compatibility tags can be found at
    `PEP 425 <https://peps.python.org/pep-0425/>`_,
    `Platform Compatibility Tags <https://packaging.python.org/en/latest/specifications/platform-compatibility-tags/>`_,
    and in the PyPA packaging page on `Tags <https://packaging.pypa.io/en/stable/tags.html>`_

    As a convenience, the following helper functions are available:

    .. py:function:: enscons.get_binary_tag()

        Returns the most specific binary tag for the current platform.

    .. py:function:: enscons.get_universal_tag()

        Returns "py2.py3-none-any" for a pure python distribution compatible with both Python 2
        and 3.

        You probably don't want to use this unless you're still supporting and testing on
        Python 2. Use ``py3-none-any`` for pure Python distributions supporting only Python 3.

    .. py:function:: get_abi3_tag()

        Returns the first abi3 tag, or the first binary tag if abi3 is not supported.

.. py:data:: WHEEL_PATH

   The directory which to build the wheel contents. Files will be copied / generated in this
   directory, and zipped into a wheel file by the :py:func:`env.WhlFile` function.

   This should be set to a directory node (``env.Dir()``). By default it is set to
   ``env.Dir("#build/wheel/")``.

.. py:data:: ROOT_IS_PURELIB

    If the wheel to create is a pure-python library, this should be set to ``True``.

    By default, this is set to ``True`` if the :py:data:`WHEEL_TAG` ends in "none-any".

    This sets the ``Root-Is-Purelib`` line in the ``WHEEL`` metadata file, and also determines
    whether "platlib" or "purelib" calls to :py:func:`env.Whl` are copied into the wheel
    path (as opposed to a data directory)


Command Line Options
--------------------

The following command line options are available. Both the ``Environment`` variable and
the command line option are given for each option. e.g. ``--wheel_dir=build`` will be
available as ``env["WHEEL_DIR"]``.

You will not usually need to set this. They are used by the PEP 517 backend to pass
information from the build frontend.

.. option:: --wheel_dir WHEEL_DIR

    ``env["WHEEL_DIR"]``

    Sets the directory which to output generated wheel files.

    Default: "dist".

.. option:: --dist_dir DIST_DIR

    ``env["DIST_BASE"]``

    Sets the directory which to output generated source distributions.

    Default: "dist"

.. option:: --egg_base EGG_INFO_PREFIX

    ``env["EGG_INFO_PREFIX"]``

    Sets the directory prefix for the :py:data:`EGG_INFO_PATH` variable. If not set,
    the value is pulled from the package metadata's ``src_root`` value. If neither is set,
    the :py:data:`EGG_INFO_PATH` directory will be created in the current directory.

Generated Environment Variables
-------------------------------
These environment variables are available after the call to :py:meth:`env.Whl`.

These variables are not settable, and are used internally by enscons. They are provided
here as a reference.

.. py:data:: WHEEL_DATA_PATH

    This is set to the ``<package name>-<package version>.data`` directory within
    :py:data:`WHEEL_PATH`

.. py:data:: DIST_INFO_PATH

    This is set to the ``<package name>-<package version>.dist-info`` directory within
    :py:data:`WHEEL_PATH`

.. py:data:: PACKAGE_NAME

    The ``name`` item from the :py:data:`PACKAGE_METADATA` dict.

.. py:data:: PACKAGE_NAME_SAFE

    The :py:data:`PACKAGE_NAME` value normalized for use as a valid filename. This is used
    as part of the wheel filename, as well as some metadata files within the wheel.

.. py:data:: PACKAGE_VERSION

    The ``version`` item from the :py:data:`PACKAGE_METADATA`

.. py:data:: PACKAGE_NAMEVER

    The :py:data:`PACKAGE_NAME_SAFE` and :py:data:`PACKAGE_VERSION` variables concatenated
    with a hyphen.

.. py:data:: WHEEL_FILE

    The final path to the wheel filename that will be generated. This is set to a file
    in the directory ``WHEEL_DIR`` with a filename generated from the package name,
    version, and compatibility tags. It can be overridden by setting the ``target`` parameter
    to :py:func:`env.WhlFile`

.. py:data:: EGG_INFO_PATH

    Path where source dist metadata is built during the creation of a source distribution.
    It's set to a name generated from the package name with ".egg-info" appended to it.
    The directory is created either in the current directory or directory set by
    :option:`--egg_base`, or the value of the package metadata's ``src_root`` key.

