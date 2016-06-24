
import sys, pkg_resources, argparse

def setup():
    """
    Adjust some command line arguments for SCons, then run.
    To be called at the bottom of a build-dependency-shim setup.py.
    """

    parser = argparse.ArgumentParser(description='setup.py arguments')
    parser.add_argument('--egg-base', action="store", dest="base")
    parser.add_argument('--python-tag', action="store", dest="python_tag")
    parser.add_argument('-d', action="store", dest="destination")
    args, unknown = parser.parse_known_args(sys.argv)

    sys.argv = unknown # pass along to SCons

    if len(sys.argv) > 1 and sys.argv[1] == 'clean':    # pip calls this
        sys.exit(0)

    # sys.argv[0] is -c not 'setup.py' with pip

    if 'egg_info' in unknown:
        sys.argv.append("=".join(['--egg-base', args.base]))

    if args.destination:
        sys.argv.append('='.join(['--wheel-base', args.destination]))

    sys.path[0:0] = ['setup-requires']
    pkg_resources.working_set.add_entry('setup-requires')

    import SCons.Script
    SCons.Script.main()
