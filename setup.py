import os.path
import setuptools

from minder import __version__ as minder_version

req_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
with open(req_path, 'rt') as f:
    install_reqs = [req.rstrip('\n') for req in f.readlines()]


setuptools.setup(
    name='minder',
    version=minder_version,
    packages=setuptools.find_packages(where='.'),
    url='https://github.com/jhannah01/minder',
    license='',
    author='Jon Hannah',
    author_email='jon@synistree.com',
    description='Simple discord.py bot for helping with remembering things',
    include_package_data=True,
    package_data={
        'minder': ['py.typed']
    },
    install_requires=install_reqs
)
