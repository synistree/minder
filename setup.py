import os.path
import setuptools

with open('README.md', 'rt') as f:
    readme_contents = f.read()

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
    package_data={
        'minder': ['py.typed']
    },
    long_description=readme_contents,
    long_description_content_type='text/markdown',
    install_requires=install_reqs,
    entry_points={
        'console_scripts': ['minder=minder.cli:run_cli']
    },
    package_dir={'': 'src'},
    packages=setuptools.find_packages(where='src'),
    include_package_data=True
)
