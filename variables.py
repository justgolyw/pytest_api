from .common import read_yaml, getcwd
from pathlib import Path


variables_path = Path(getcwd()) / Path("variables.yml")
variables = {}
if variables_path.exists():
    variables = read_yaml(variables_path)

