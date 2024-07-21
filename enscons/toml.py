"""
Import available toml.load 
"""
try:
    # Python 3.11+
    from tomllib import load
except ImportError:
    from tomli import load
