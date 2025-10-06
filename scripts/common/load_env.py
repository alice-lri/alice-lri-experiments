from pathlib import Path
from dotenv import load_dotenv
import os

def load_env():
    current = Path.cwd()

    for parent in [current] + list(current.parents):
        env_file = parent / ".env"
        if env_file.exists():
            os.environ["PROJECT_ROOT"] = str(parent)
            load_dotenv(dotenv_path=env_file, override=True)
            return parent

    raise FileNotFoundError(".env not found in this directory tree.")

# TODO consider including container.sif and databses as git lfs