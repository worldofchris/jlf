from setuptools import setup

setup(
    name = "JIRA lean forward",
    version = "0.1.1dev",
    description = "Get Lean Stats like throughput and cycle time out of jira with ease",
    author = "Chris Young",
    licence = "BSD",
    author_email = "chris@chrisyoung.org",
    platforms = ["Any"],
    packages = ['jira_stats'],
    include_package_data = True,
    install_requires=[
        'argparse==1.2.1',
        'ipython==0.13.2',
        'jira-python==0.13',
        'mockito==0.5.1',
        'numpy==1.7.1',
        'oauthlib==0.4.0',
        'pandas==0.11.0',
        'python-dateutil==1.5',
        'pytz==2013b',
        'requests==1.2.0',
        'requests-oauthlib==0.3.1',
        'six==1.3.0',
        'tlslite==0.4.1',
        'wsgiref==0.1.2',
        'xlwt==0.7.5'
    ]
)
