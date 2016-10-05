from setuptools import setup
from setuptools.command.build_ext import build_ext as _build_ext
import inspect
from subprocess import call

class build_ext(_build_ext):
    # Taken from http://stackoverflow.com/a/21621689/1064619
    def finalize_options(self):
        _build_ext.finalize_options(self)
        # Prevent numpy from thinking it is still in its setup process:
        __builtins__.__NUMPY_SETUP__ = False
        import numpy
        self.include_dirs.append(numpy.get_include())

setup(
    name="Just lean forward",
    version="0.1.3dev",
    description="Get Lean Stats like throughput and cycle time out of Jira/FogBugz/Trello with ease",
    author="Chris Young",
    license="LICENSE.md",
    author_email="chris@chrisyoung.org",
    platforms=["Any"],
    packages=['jlf_stats'],
    include_package_data=True,
    scripts=['bin/jlf', 'bin/patch_trello'],
    setup_requires=['numpy'],
    zip_safe=False,
    data_files=['patches', ['boards.py.diff']],
    install_requires=[
        'requests',
        'nose',
        'mock',
        'argparse==1.2.1',
        'ipython==0.13.2',
        'fogbugz',
        'jira',
        'numpy',
        'openpyxl==1.6.2',
        'pandas==0.13.1',
        'python-dateutil==1.5',
        'pytz==2013b',
        'six==1.9.0',
        'xlrd==0.9.2',
        'xlwt==0.7.5',
        'XlsxWriter',
        'trello==0.9.1'
    ]
)

