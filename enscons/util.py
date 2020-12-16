"""
Utilities otherwise provided by pkg_resources or wheel
"""

from pkg_resources import safe_name, safe_extra, to_filename
from packaging.requirements import Requirement

# from wheel
def requires_to_requires_dist(requirement):
    """Return the version specifier for a requirement in PEP 345/566 fashion."""
    if getattr(requirement, "url", None):
        return " @ " + requirement.url

    requires_dist = []
    for op, ver in requirement.specs:
        requires_dist.append(op + ver)
    if not requires_dist:
        return ""
    return " (%s)" % ",".join(sorted(requires_dist))


def generate_requirements(extras_require):
    """
    Convert requirements from a setup()-style dictionary to ('Requires-Dist', 'requirement')
    and ('Provides-Extra', 'extra') tuples.

    extras_require is a dictionary of {extra: [requirements]} as passed to setup(),
    using the empty extra {'': [requirements]} to hold install_requires.
    """
    for extra, depends in extras_require.items():
        condition = ""
        extra = extra or ""
        if ":" in extra:  # setuptools extra:condition syntax
            extra, condition = extra.split(":", 1)

        extra = safe_extra(extra)
        if extra:
            yield "Provides-Extra", extra
            if condition:
                condition = "(" + condition + ") and "
            condition += "extra == '%s'" % extra

        for dependency in depends:
            new_req = Requirement(dependency)
            if condition:
                if new_req.marker:
                    new_req.marker = "(%s) and %s" % (new_req.marker, condition)
                else:
                    new_req.marker = condition
            yield "Requires-Dist", str(new_req)
