# -*- coding: utf-8 -*-
'''
功能： api接口案例收集和执行
原理： 使用pytest的mock功能 pytest_collect_file
'''

import json
import re
import pytest
from env import get_envs
from common import read_yaml
from runner import ApiRunner, Runner, ExecRunner

# 定义一个执行机
runner = Runner()
# 先注册命令执行
runner.register_handler("exec", ExecRunner)

# 是否debug输出
debug = False


def pytest_addhooks(pluginmanager):
    import hooks

    pluginmanager.add_hookspecs(hooks)


def pytest_addoption(parser):
    '''
    pytest命令增加两个参数，支持指定api的ip、端口、url前缀，方便命令行执行
    '''
    parser.addoption("--host", action="store", help="待测试的API的HOST，可填写IP或者域名")
    parser.addoption("--port", action="store", help="待测试的API的PORT", default=443)
    parser.addoption("--user", action="store", help="待测试的API的basic认证用户名，携带会覆盖env.yml里面的账号，默认为空",
                     default="")
    parser.addoption("--password", action="store", help="待测试的API的basic的密码，携带会覆盖env.yml里面的密码，默认为空",
                     default="")
    parser.addoption("--pdebug", action="store", help="是否打印错误信息堆栈", default=False)
    parser.addoption("--step-name", action="store", help="指定步骤执行，包括前后置中的步骤", default="")
    parser.addoption("--exclude", action="store", help="要排除的标签", default="")
    parser.addoption("--include", action="store", help="要包括的标签", default="")


def pytest_collect_file(path, parent):
    """
    定义yml后缀，会被认为是接口案例文件
    :param path: 文件全路径
    :param parent: session
    :return: collector
    """
    if path.ext == ".yml" and not is_ignore_file(path):
        return YamlFile.from_parent(parent, fspath=path)


@pytest.mark.hookwrapper
def pytest_runtest_makereport(item):
    # 解决乱码
    outcome = yield
    report = outcome.get_result()
    getattr(report, 'extra', [])
    report.nodeid = report.nodeid.encode("unicode_escape").decode("utf-8")


def is_ignore_file(path):
    api_ignores = ["variables.yml", "env.yml"]
    return path.basename in api_ignores


class YamlFile(pytest.File):

    def collect(self):
        '''
        collector调用collect方法, 会从文件中提取Item对象, 即testcase
        :return: [Items]
        '''
        # 注册执行
        # 读取环境变量
        envs = get_envs(self.config)
        self._register_hander(envs)

        # 添加HOST, PORT和协议、用户名和密码等全局信息到全局变量中
        self._add_global_variables(envs)

        # 是否要打印debug堆栈
        global debug
        debug = self.config.getoption("--pdebug")

        # 收集案例
        case = read_yaml(self.fspath)

        setup = case["setup"] if "setup" in case else []
        teardown = case["teardown"] if "teardown" in case else []
        tags = case["tags"] if "tags" in case else []
        # 过滤exclude标签的案例，包含则跳过
        if self._is_exclude(tags):
            return

        # 收集只包含include的标签
        if self._is_include(tags):
            step_name = self.config.getoption("--step-name")
            yield YamlItem.from_parent(self, name=case["name"],
                                       steps=case["steps"],
                                       setup=setup,
                                       teardown=teardown,
                                       step_name=step_name)

    def _add_global_variables(self, envs):
        """
        把全局性的IP，PORT，协议写入到全局变量中
        """
        global variables
        variables["IP"] = self.config.getoption("--host")
        variables["PORT"] = self.config.getoption("--port")
        variables["PROTO"] = envs["proto"]

    def _register_hander(self, envs):
        """
        注册api执行器
        """
        auth = envs["auth"]
        if auth:
            # 如果存在basic授权信息，则把用户信息写入全局变量
            global variables
            variables["USER"] = auth[0]
            variables["PASSWORD"] = auth[1]

        runner.register_handler("api", ApiRunner)

    def _is_exclude(self, tags):
        exclude = self.config.getoption("--exclude")
        if exclude == "":
            return False
        exclude_tags = exclude.split(",")
        for exclude_tag in exclude_tags:
            return exclude_tag in tags
        return False

    def _is_include(self, tags):
        include = self.config.getoption("--include")
        if include == "":
            return True
        flag = False
        include_tags = include.split(",")
        for include_tag in include_tags:
            if include_tag in tags:
                flag = True
                break
        return flag


class YamlItem(pytest.Item):

    def __init__(self, parent, **kw):
        super().__init__(kw["name"], parent)
        self.setups = kw["setup"]
        self.steps = kw["steps"]
        self.teardowns = kw["teardown"]
        self.step_name = kw["step_name"]
        self._global_params = variables

    def _re_step(self, step):
        '''
        变量替换
        @param step 步骤信息
        @return 替换后的步骤信息
        '''
        step_json = json.dumps(step)
        for k, v in self._global_params.items():
            re_str = r"\"\$\{" + k + r"\}\""
            re_str_2 = r"\\\"\$\{" + k + r"\}\\\""  # 为了给已有的案例做兼容
            param_str = json.dumps(v)
            if isinstance(v, str):
                re_str = r"\$\{" + k + r"\}"
                param_str = v

            # 兼容以前的url中带变量类似"${continue}"这种写法
            step_json = re.sub(re_str_2, param_str, step_json)
            # 新写法 去掉引用 ${continue}
            step_json = re.sub(re_str, param_str, step_json)

        return json.loads(step_json, strict=False)

    def _run(self, steps, is_teardown=False):
        step_name_prefix = "执行步骤"
        if is_teardown:
            step_name_prefix = "执行后置"
        for index, step in enumerate(steps):
            step_msg = f"{step_name_prefix}{index}：{step['name']} 结果: Failed ✘ ,"
            if "skip" in step and step["skip"]:
                continue
            if self.step_name in step["name"]:
                try:
                    step = self._re_step(step)
                    res_params = runner.run(step, self.config)
                    self._global_params.update(res_params)
                except AssertionError as e:
                    step_msg += f"具体信息: {e}"
                    if not is_teardown:
                        raise YamlException(step_msg)
                    else:
                        print(f'{step_msg}具体信息是: {e}')
                except Exception as e:
                    step_msg += f"具体信息: {e}"
                    if not is_teardown:
                        raise YamlException(step_msg)
                    else:
                        print(f'{step_msg}具体信息是: {e}')

    def setup(self):
        '''
        案例前置条件
        '''
        pass

    def teardown(self):
        '''
        Item 对象的清理步骤
        '''
        self._run(self.teardowns, True)

    def runtest(self):
        '''
        执行Item对象时, 会调用runtest方法
        所以这里定义具体的测试行为
        :return
        '''
        self._run(self.setups)
        self._run(self.steps)

    def repr_failure(self, excinfo):
        """ called when self.runtest() raises an exception. """
        if isinstance(excinfo.value, YamlException):
            return f"案例执行失败：{excinfo.value}"
        else:
            if debug:
                print(excinfo.traceback)
            return f"案例执行，失败信息是：{excinfo}"

    def reportinfo(self):
        return self.fspath, 0, "用例: {}".format(self.name)


class YamlException(Exception):
    pass
