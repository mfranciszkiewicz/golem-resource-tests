from distutils.core import setup

setup(
    name='golem-resource-tests',
    version='0.1',
    description='Resource sharing application test utility for the Golem project (http://golem.network)',
    author='Marek Franciszkiewicz',
    author_email='marek@golem.network',
    packages=['common', 'monitor', 'network', 'resources'],
)
