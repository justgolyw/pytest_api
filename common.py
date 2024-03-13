import os
from pathlib import Path

import yaml


class Loader(yaml.FullLoader):
    """
    增加支持 !import的语法解析
    """

    def import_yml(self, node):
        file_path = Path(self.name).parent / Path(node.value)
        with open(file_path, "r", encoding="utf-8") as f:
            return yaml.load(f, Loader)

# 增加自定义标签!import
Loader.add_constructor("!import", Loader.import_yml)


def getcwd():
    return os.getcwd()


def read_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.load(f, Loader=Loader)


def yaml_load(content):
    return yaml.load(content, Loader=Loader)


def json_check(ori, expt, is_container_compare=False):
    '''
    @params ori 源数据
    @params expt  期望数据
    @params is_container_compare  字符串对比方式是否采用包含方式，默认是非包含方式对比
    json 字符串包含关系判断，是否ori 包含 expt
    '''
    if isinstance(ori, dict):
        """若为字典模式"""
        for key, value in expt.items():
            if "err_code" in expt:
                continue
            assert key in ori, f"返回值校验失败，数据：{ori}, 返回值中没有要校验对象: {key}"
            json_check(ori[key], value, is_container_compare)
    elif isinstance(ori, list):
        assert len(ori) == len(expt), f"返回值校验失败，校验的数组长度已经超出返回的数组长度。" \
            f"期望值: {expt},实际值{ori}"
        for index, exptItem in enumerate(expt):
            json_check(ori[index], exptItem, is_container_compare)
    elif isinstance(ori, str):
        if is_container_compare:
            assert expt in ori, f"返回值校验失败：期望值：{expt}, 实际值：{ori}, 非包含关系"
        else:
            assert ori == expt, f"返回值校验失败：期望值：{expt}, 实际值：{ori}"
    else:
        assert ori == expt, f"返回值校验失败：期望值：{expt}, 实际值：{ori}"