"""The resume-optimizer package."""

from importlib.metadata import version

# pyproject.toml holds the only copy of the version. There is no fallback on purpose:
# importing the package without it installed raises.
__version__ = version("resume-optimizer")
