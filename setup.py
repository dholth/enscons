#!/usr/bin/env python
# Install dependencies listed in pyproject.toml, then
# continue with regularly scheduled setup.py.
# From https://bitbucket.org/dholth/setup-requires

import sys, subprocess, pkg_resources

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
import enscons.setup
enscons.setup.setup()
