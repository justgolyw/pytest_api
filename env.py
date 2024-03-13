from pathlib import Path
from collections import ChainMap
# from .common import read_yaml, getcwd
from pytest_api.common import read_yaml, getcwd


defaults_envs = {
    "proto": "https",
    "container_compare": True,
    "urlprefix": "",
    "headers": None,
    "auth": None
}


def get_envs_from_yml():
    env_path = Path(getcwd()) / Path("env.yml")
    envs = {}
    if env_path.exists():
        envs = read_yaml(env_path)
    return envs


def get_envs_from_cmd(config):
    user = config.getoption("--user")
    password = config.getoption("--password")
    if user and password:
        return {
            "auth": [user, password]
        }
    else:
        return {}


def get_envs(config):
    """
    优先从命令行获取，没有则从yml文件文件，再没有从默认值中获取
    """
    yml_envs = get_envs_from_yml()
    cmd_envs = get_envs_from_cmd(config)
    # 使用ChainMap可以用来合并两个或者更多个字典, 当查询的时候，从前往后依次查询
    # ChainMap进行修改的时候总是只会对第一个字典进行修改
    envs = ChainMap(cmd_envs, yml_envs, defaults_envs)
    return envs