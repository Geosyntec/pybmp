# Setup script for the pybmpdb package
#
# Usage: python setup.py install
#
import os
from setuptools import setup, find_packages


def getDataFiles(folder):
    files = [d for d in map(
        lambda x: os.path.join(folder, x),
        os.listdir(folder)
    )]
    return files



DESCRIPTION = "pybmpdb: Analyze data from the International Stormwater BMP Database"
LONG_DESCRIPTION = DESCRIPTION
NAME = "pybmpdb"
VERSION = "0.1"
AUTHOR = "Paul Hobson (Geosyntec Consultants)"
AUTHOR_EMAIL = "phobson@geosyntec.com"
URL = "https://github.com/Geosyntec/pybmpdb"
DOWNLOAD_URL = "https://github.com/Geosyntec/pybmpdb/archive/master.zip"
LICENSE = "BSD 3-clause"
PACKAGES = find_packages(exclude=[])
PLATFORMS = "Python 2.7, 3.3 and later."
CLASSIFIERS = [
    "License :: OSI Approved :: BSD License",
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    "Intended Audience :: Science/Research",
    "Topic :: Software Development :: Libraries :: Python Modules",
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3.3',
    'Programming Language :: Python :: 3.4',
]
INSTALL_REQUIRES = ['wqio']
PACKAGE_DATA = {
    'pybmpdb.data': ['*.csv'],
    'pybmpdb.tex': ['*.tex'],
}


setup(
    name=NAME,
    version=VERSION,
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    url=URL,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    download_url=DOWNLOAD_URL,
    license=LICENSE,
    packages=PACKAGES,
    package_data=PACKAGE_DATA,
    platforms=PLATFORMS,
    classifiers=CLASSIFIERS,
    install_requires=INSTALL_REQUIRES,
)
