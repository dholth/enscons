"""
Command-line interface for PEP 517 builders.

Invokes build against any [build-backend], not just enscons.

See also the more complete https://github.com/pypa/pep517 utility.

See also enscons.api.

Install enscons[cli] for dependencies.
"""

import sys
import pprint
import os.path
import click
import pytoml as toml


class Backend(object):
    def __init__(self):
        self.metadata = dict(toml.load(open("pyproject.toml")))
        build_backend = self.metadata["build-system"]["build-backend"]
        module, _, obj = build_backend.partition(":")
        __import__(module)
        build_module = sys.modules[module]
        if obj:
            self._impl = getattr(build_module, obj)
        else:
            self._impl = build_module

    def __getattr__(self, key):
        return getattr(self._impl, key)


@click.group()
def cli():
    pass


@click.command()
def info():
    b = Backend()
    click.echo(pprint.pformat(b._impl.__dict__))


@click.command()
@click.option("--metadata-dir", default="dist", help="Target directory for wheel")
def metadata(metadata_dir):
    """Prepare metadata from a wheel."""
    metadata_name = Backend().prepare_metadata_for_build_wheel(metadata_dir, {})
    click.echo(os.path.join(metadata_dir, metadata_name) + "\n")


@click.command()
@click.option("--wheel-dir", default="dist", help="Target directory for wheel")
def wheel(wheel_dir):
    """Build a wheel."""
    wheel_name = Backend().build_wheel(wheel_dir, {})
    click.echo(os.path.join(wheel_dir, wheel_name) + "\n")


@click.command()
@click.option("--dist-dir", default="dist", help="Target directory for sdist")
def sdist(dist_dir):
    """Build a source distribution."""
    sdist_name = Backend().build_sdist(dist_dir, {})
    click.echo(os.path.join(dist_dir, sdist_name) + "\n")


cli.add_command(info)
cli.add_command(metadata)
cli.add_command(wheel)
cli.add_command(sdist)

if __name__ == "__main__":
    cli()
