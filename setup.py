from setuptools import setup, find_packages
from bcl2fastq import __version__
import os

def read_file(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='bcl2fastq',
    version=__version__,
    description="Micro-service for running bcl2fastq",
    long_description=read_file('README'),
    keywords='bioinformatics',
    author='SNP&SEQ Technology Platform, Uppsala University',
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        'console_scripts': ['bcl2fastq-ws = bcl2fastq.app:start']
    }
)
