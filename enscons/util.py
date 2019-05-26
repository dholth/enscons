"""
Utilities otherwise provided by pkg_resources or wheel
"""

from pkg_resources import safe_name, safe_extra, to_filename, Requirement


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


def convert_requirements(requirements):
    """Yield Requires-Dist: strings for parsed requirements strings."""
    for req in requirements:
        parsed_requirement = Requirement.parse(req)
        spec = requires_to_requires_dist(parsed_requirement)
        extras = ",".join(sorted(parsed_requirement.extras))
        if extras:
            extras = "[%s]" % extras
        yield (parsed_requirement.project_name + extras + spec)


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

        if condition:
            condition = " ; " + condition

        for new_req in convert_requirements(depends):
            yield "Requires-Dist", new_req + condition
