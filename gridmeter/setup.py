import os
from setuptools import setup, find_packages

OFF_DATAFLOW_REQUIRES = []

INSTALL_REQUIRES = [
    "attrs",
    "numpy>=1.24.4",
    "scipy>=1.10.1",
    "pandas>=1.1.0",
    "numba",
    "scikit-learn>=1.3.0",
    "scikit-fda>=0.8.0",
    "pydantic>=2.0.0",
    "eval_type_backport",
]
EXTRAS_REQUIRE = {"off-dataflow": OFF_DATAFLOW_REQUIRES}

here = os.path.abspath(os.path.dirname(__file__))
NAME = "gridmeter"
about = {}

with open(os.path.join(here, NAME, "__version__.py")) as f:
    exec(f.read(), about)

setup(
    name="gridmeter",
    version=about["__version__"],
    description=about["__description__"],
    url=about["__url__"],
    author=about["__author__"],
    classifiers=[],
    packages=find_packages(),
    install_requires=INSTALL_REQUIRES,
    extras_require=EXTRAS_REQUIRE,
)
