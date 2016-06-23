#!/usr/bin/env python
# Install dependencies listed in pyproject.toml, then
# continue with regularly scheduled setup.py.
# From https://bitbucket.org/dholth/setup-requires

import sys, subprocess, pkg_resources, argparse

DEBUG=False

if sys.argv[1] == 'clean':
    sys.exit(0)

parser = argparse.ArgumentParser(description='setup.py arguments')
parser.add_argument('--egg-base', action="store", dest="base")
parser.add_argument('-d', action="store", dest="destination")
args, unknown = parser.parse_known_args(sys.argv)

sys.argv = unknown # pass along to SCons

# sys.argv[0] is -c not 'setup.py' with pip

if 'egg_info' in unknown:
    sys.argv.append("=".join(['--egg-base', args.base]))

if args.destination:
    sys.argv.append('='.join(['--wheel-base', args.destination]))

if DEBUG:    
    with open('/tmp/arglog.txt', 'a') as f:
        f.write('parsed, unknown, new ' + '\n'.join((repr(args), repr(unknown), repr(sys.argv))) + '\n')    

sys.path[0:0] = ['setup-requires']
pkg_resources.working_set.add_entry('setup-requires')

def missing_requirements(specifiers):
    for specifier in specifiers:
        try:
            pkg_resources.require(specifier)
        except pkg_resources.DistributionNotFound:
            yield specifier

def install_requirements(specifiers):
    to_install = list(specifiers)
    if to_install:
        subprocess.call([sys.executable, "-m", "pip", "install", 
            "-t", "setup-requires"] + to_install)
        
install_requirements(missing_requirements(['pytoml']))

import pytoml

try:
    with open('pyproject.toml') as f:
        pyproject = pytoml.load(f)
except IOError:
    pass
else:
    requires = pyproject.get('build-system', {}).get('requires')
    install_requirements(missing_requirements(requires))

### Place normal setup.py contents below ###

import SCons.Script
SCons.Script.main()

