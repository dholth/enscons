#!/usr/bin/env python
# Pull arguments out of setup.py by monkeypatching setuptools.
# Run in a directory with setup.py to get a pyproject.toml on stdout.
# Daniel Holth <dholth@fastmail.fm>, 2016

from __future__ import print_function, absolute_import

from collections import OrderedDict
import setuptools, distutils.core, pprint, sys, pytoml

def main():

    def setup_(**kw):
        setup_.arguments = kw

    setuptools.setup = setup_
    distutils.core.setup = setup_

    sys.path[0:0] = '.'

    import setup

    # Convert the keys that enscons uses and a few more that are serializable.
    key_order = ['name', 'version', 'description', 'classifiers', 'keywords',
        'author', 'author_email', 'url', 'license', 'install_requires',
        'extras_require', 'tests_require', 'entry_points', 'long_description' ]

    ordered_arguments = OrderedDict()
    for key in key_order:
        if key in setup_.arguments:
            ordered_arguments[key] = setup_.arguments.pop(key)

    if isinstance(ordered_arguments['keywords'], str):
        ordered_arguments['keywords'] = ordered_arguments['keywords'].split()

    pyproject = pytoml.dumps(OrderedDict(
            [
            ['tool', {'enscons': ordered_arguments}],
            ['build-system', {'requires': ['pytoml>=0.1', 'enscons']}],
            ]), sort_keys=False)

    print(pyproject)

if __name__ == '__main__':
    main()
