import os.path
import setuptools


install_reqs = []
req_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')

with open(req_path, 'rt') as f:
    for req in f.readlines():
        req = req.rstrip('\n')
        if req.startswith('#') or '-e ' in req:
            # Skip commented out lines and anything with "-e" in the name
            continue

    install_reqs.append(req)


setuptools.setup(
    name='minder',
    packages=setuptools.find_namespace_packages(where='.'),
    url='https://github.com/jhannah01/minder',
    author='Jon Hannah',
    author_email='jon@synistree.com',
    description='Simple discord.py bot for helping with remembering things',
    include_package_data=True,
    package_data={
        'minder': ['py.typed']
    },
    install_requires=install_reqs,
    entry_points={
        'console_scripts': ['minder=minder.cli:run_cli']
    }
)
