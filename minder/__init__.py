import os.path

from dotenv import load_dotenv

__version__ = '0.0.1'

if not load_dotenv():
    raise RuntimeError(f'No ".env" file found in "{os.path.abspath(".")}"')
