
import sys, pkg_resources, argparse

def develop(path):
    """
    Add distribution on path to easy-install.pth for development, like setup.py develop.
    A single egg-info should exist in path.
    This may work fine with a .dist-info directory in place of .egg-info.
    """
    import os
    from setuptools.command import easy_install
    from . import paths

    pathdir = paths.get_install_paths('enscons')['purelib']
    pathfile = os.path.join(pathdir, 'easy-install.pth')

    pthdistributions = easy_install.PthDistributions(pathfile)
    # distribution = Distribution(
    #     target,
    #     PathMetadata(target, os.path.abspath(ei.egg_info)),
    #     project_name=ei.egg_name)
    distribution = list(pkg_resources.find_distributions(path, True))[0]
    pthdistributions.add(distribution)
    pthdistributions.save()

    egg_link = os.path.join(pathdir, distribution.project_name + '.egg-link')
    egg_path = os.path.abspath(path)
    with open(egg_link, "w") as f:
        f.write(egg_path + "\n" + '.')
        f.close()

def setup():
    """
    Adjust some command line arguments for SCons, then run.
    To be called at the bottom of a build-dependency-shim setup.py.
    """

    parser = argparse.ArgumentParser(description='setup.py arguments')
    parser.add_argument('--egg-base', action="store", dest="base")
    parser.add_argument('--python-tag', action="store", dest="python_tag")
    parser.add_argument('--formats', type=str, action="store", dest="sdist_formats")
    parser.add_argument('--dist-dir', type=str, action="store", dest="sdist_dir")
    parser.add_argument('-d', action="store", dest="destination")
    parser.add_argument('--no-deps', action="store_true", dest="no_deps")
    parser.add_argument('--single-version-externally-managed', action="store_true")
    parser.add_argument('--compile', action="store_true")
    parser.add_argument('--install-headers', action="store")
    parser.add_argument('--record', action="store")
    args, unknown = parser.parse_known_args(sys.argv)

    sys.argv = unknown # pass along to SCons

    if len(sys.argv) > 1 and sys.argv[1] == 'clean':    # pip calls this
        sys.exit(0)

    # sys.argv[0] is -c not 'setup.py' with pip

    # Convert certain arguments into =-separated format
    for flag, arg in (
            ('--dist-dir', 'sdist_dir'),
            ('--wheel-dir', 'destination'),
            ('--egg-base', 'base'),
            ):
        if getattr(args, arg):
            sys.argv.append('='.join((flag, getattr(args, arg))))

    if 'develop' in sys.argv:
        src_root = '.'
        import pytoml
        with open('pyproject.toml', 'r') as pyproject:
            metadata = pytoml.load(pyproject)
            src_root = metadata['tool']['enscons'].get('src_root', src_root)
        develop(src_root)
        sys.argv.remove('develop')

    sys.path[0:0] = ['setup-requires']
    pkg_resources.working_set.add_entry('setup-requires')

    import SCons.Script
    SCons.Script.main()

# Command used when installing from a source directory:
"""
"python3.5 -u -c "import setuptools, tokenize
__file__='/tmp/pip-6s1w5sd2-build/setup.py'
exec(compile(getattr(tokenize, 'open', open)(__file__).read().replace('\r\n', '\n'), __file__, 'exec'))"
install --record /tmp/pip-795f8wqp-record/install-record.txt
--single-version-externally-managed
--compile
--install-headers /home/dholth/prog/cryptacular/.tox/py35/include/site/python3.5/enscons
"""
