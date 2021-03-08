import os.path

from dotenv import load_dotenv

if not load_dotenv():
    raise RuntimeError(f'No ".env" file found in "{os.path.abspath(".")}"')
