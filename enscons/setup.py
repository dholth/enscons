
import sys, pkg_resources, argparse

def develop(path):
    """
    Add distribution on path to easy-install.pth for development, like setup.py develop.
    A single egg-info should exist in path.
    This may work fine with .dist-info
    """
    import os, wheel.paths
    from setuptools.command import easy_install

    pathdir = wheel.paths.get_install_paths('enscons')['purelib']
    pathfile = os.path.join(pathdir, 'easy-install.pth')
    pthdistributions = easy_install.PthDistributions(pathfile)
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
    parser.add_argument('-d', action="store", dest="destination")
    parser.add_argument('--no-deps', action="store_true", dest="no_deps")
    args, unknown = parser.parse_known_args(sys.argv)

    sys.argv = unknown # pass along to SCons

    if len(sys.argv) > 1 and sys.argv[1] == 'clean':    # pip calls this
        sys.exit(0)

    # sys.argv[0] is -c not 'setup.py' with pip

    if 'egg_info' in unknown and args.base:
        sys.argv.append("=".join(['--egg-base', args.base]))

    if 'develop' in unknown:
        develop('.')
        sys.exit(0)

    if args.destination:
        sys.argv.append('='.join(['--wheel-base', args.destination]))

    sys.path[0:0] = ['setup-requires']
    pkg_resources.working_set.add_entry('setup-requires')

    import SCons.Script
    SCons.Script.main()
