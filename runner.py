import json
import time
import subprocess
from requests.utils import dict_from_cookiejar

from .env import get_envs
from .common import json_check, getcwd
from .request import ApiRequest

# 获取全局对比方式
container_compare = True


class CheckMixIn():
    """
    结果校验MixIn
    """

    def _json_check(self, obj, exptResponse):
        """
        JSON字段校验
        @param obj           dict       返回的结果信息
        @param exptResponse  str|dict   期望的结果信息
        """
        global container_compare
        if isinstance(exptResponse["json"], dict):
            json_check(obj, exptResponse["json"],
                       container_compare)
        else:
            assert False, f'期望结果：{exptResponse["json"]}非json结构'

    def _text_check(self, text, exptResponse):
        """
        文本校验
        @param text          str   返回的结果信息
        @param exptResponse  str   期望的结果信息
        """
        assert str(exptResponse["text"]) in text, f'期望结果：' \
            f'{str(exptResponse["text"])}, 实际结果: {text}'

    def _json_text_check(self, response, exptResponse):
        """
        json和文本校验
        @param response      obj        返回的结果信息
        @param exptResponse  str        期望的结果信息
        """
        if "json" in exptResponse:
            self._json_check(self.get_response_json(response), exptResponse)
        if "text" in exptResponse:
            self._text_check(self.get_response_text(response), exptResponse)

class ReturnMixIn():
    """
    返回值处理
    """
    def _get_json_value_by_rule(self, obj, rule):
        '''
        @param obj      dict    请求的返回值的json字典结构
        @param rule     str     获取变量的规则，规则可能是a.b.c | a | a.b.1 嵌套获取
        '''
        value = None
        for key in rule.split("."):
            if key.isdigit():
                try:
                    value = obj[int(key)]
                    obj = value
                except IndexError:
                    raise AssertionError(f"请检查返回值规则:{rule} 中的{key}，超过数组长度")
            else:
                if key in obj:
                    value = obj[key]
                    obj = value
                else:
                    raise AssertionError(f"请检查返回值规则:{rule} 中的key:{key} 不存在")
        return value

    def _return(self, response, return_rule):
        '''
        @param response       请求的返回值
        @param return_rule    返回规则
        '''
        res_param = {}
        response_is_json = True
        try:
            response_json = self.get_response_json(response)
        except AssertionError:
            response_is_json = False
        if response_is_json:
            # 获取返回json
            # 遍历规则，取每个规则value值当做返回值的key取返回值中的数据
            for key, value in return_rule.items():
                res_value = self._get_json_value_by_rule(response_json, value)
                if res_value:
                    res_param[key] = res_value
        else:
            # 如果是文本，则直接把return的值，当做变量的名称，返回的文件当做变量的值
            res_param[return_rule] = self.get_response_text(response)
        return res_param

    def get_cookie(self, response):
        cookies = response.cookies
        return dict_from_cookiejar(cookies)

    def _return_header(self, response, return_rule):
        '''
        :param response: 请求的返回值
        :param return_rule: 规则类似: mycookie: cookie, mytoken: token ，其中value是头部的key
        :return:
        '''
        res_param = {}
        headers = response.headers
        for key, value in return_rule.items():
            res_value = None
            if value.lower() == "cookie":
                res_value = self.get_cookie(response)
            elif value.lower() == "set-cookie":
                res_value = headers['Set-Cookie'].split(";")[0]
            else:
                res_value = headers[value]
            if res_value:
                res_param[key] = res_value
        return res_param


class RunerMixin():

    def run(self, step):
        res_param = {}
        # 发送请求
        assert "request" in step, "步骤中必须要有request字段，请检查当前yml文件"
        r = self._run(step["request"])
        # 请求对比
        if "response" in step:
            self._resonse_compare(r, step["response"])
        # 返回值处理
        if "return" in step:
            res_param = self._return(r, step["return"])
        if "return_header" in step:
            res_param.update(self._return_header(r, step["return_header"]))
        return res_param

class ApiRunner(ApiRequest, CheckMixIn, ReturnMixIn, RunerMixin):
    """
    API 步骤的格式是：
    api:
      request:
        url: /api/v1/test        # 必选
        method: GET              # 必选
        headers: {"test": "a"}   # 可选
        auth: ["admin", "admin"] # 可选
        data: test               # 可选,和json二选一
        json: {"a":1}            # 可选
      response:
        status_code: 200         # 可选
        json: {"a":1}            # 可选 和 text二选一
        text: test               # 可选
      return:                    # 可选，当前会从response的json或者text取
        var_a: a                 # 可选，返回变量var_a
        var_b: a.b.1             # 可选
    """

    @classmethod
    def from_config_and_env(cls, config):
        envs = get_envs(config)
        urlprefix = envs["urlprefix"]
        proto = envs["proto"]
        headers = envs["headers"]
        global container_compare
        container_compare = envs["container_compare"]
        # obj = cls(config.getoption("--host"),
        #           config.getoption("--port"),
        #           urlprefix
        #           )
        obj = cls(envs["host"],
                  envs["port"],
                  urlprefix
                  )
        print("obj=", obj)
        auth = envs["auth"]
        if isinstance(auth, list):
            obj.auth = tuple(auth)
        else:
            if auth:
                print("授权格式错误，请检查")
        obj.headers = headers
        obj.proto = proto
        return obj

    def _run(self, request):
        '''
        发送请求
        '''
        return self.send(**request)

    def get_response_json(self, response):
        try:
            return response.json()
        except json.decoder.JSONDecodeError:
            raise AssertionError(
                f"返回非json结构，当前状态码为:{response.status_code}, 内容为{response.text}")

    def get_response_text(self, response):
        return response.text

    def _resonse_compare(self, response, exptResponse):
        '''
        @param response       请求的返回值
        @param exptResponse   期望返回值，即yaml里面的response
        '''
        if "status_code" in exptResponse:
            self._compare_status_code(response.status_code, exptResponse[
                "status_code"], response.text)
        self._json_text_check(response, exptResponse)

    def _compare_status_code(self, status_code, expt_status_code, text):
        '''
        状态码校验支持多状态码校验，比如同时有200和400,只要有一个校验通过，就是通过
        '''
        if isinstance(expt_status_code, int):
            assert status_code == expt_status_code,\
                f'状态码不一致：期望值:{expt_status_code},' \
                f'实际值: {status_code}， 返回内容:{text}'
        elif isinstance(expt_status_code, str):
            ok = False
            for code in expt_status_code.split(","):
                if int(code) == status_code:
                    ok = True
                    break
            assert ok, f'状态码不一致：期望值:{expt_status_code},' \
                f'实际值: {status_code}， 返回内容:{text}'


class ExecRunner(CheckMixIn, ReturnMixIn, RunerMixin):
    """
    执行外部命令，扩展执行器
    exec:
      request:
        args: python test.py 或者 ["python", "test.py"]  # 必选
        cwd:  /tmp                                       # 可选
        shell: False                                     # 可选
      response:                                          # 同API是个校验字段
        text: test                                       # 返回文本和json是互斥关系
        json: {"a": "b"}                                 # 返回json和文本是互斥关系
      return:                                            # 获取返回值
        var_a: a                                         # 返回值变量处理
    """

    @classmethod
    def from_config_and_env(cls, config):
        return cls()

    def _run(self, request):
        assert "args" in request, "args为命令扩展动作的必选传参，请检查当前的yml文件"
        args = request["args"]
        cwd = request["cwd"] if "cwd" in request else getcwd()
        shell = request["shell"] if "shell" in request else False
        res = subprocess.check_output(args, shell=shell, cwd=cwd)
        try:
            return res.decode("utf-8")
        except UnicodeDecodeError:
            return res.decode('gbk')

    def _resonse_compare(self, response, exptResponse):
        self._json_text_check(response, exptResponse)

    def get_response_json(self, response):
        try:
            return json.loads(response)
        except json.decoder.JSONDecodeError:
            raise AssertionError(
                f"返回非json结构，内容为{response}")

    def get_response_text(self, response):
        return response

class Runner:

    def __init__(self):
        self.handlers = {}
        self.config = None

    def register_handler(self, key, handler):
        self.handlers[key] = handler

    def run(self, step, config):
        res_param = {}
        for k in step:
            if k == "name":
                continue
            if k == "sleep":
                time.sleep(int(step[k]))
                continue
            if k not in self.handlers:
                # 获取环境变量
                env = get_envs(config)
                res_param_arr = config.hook.pytest_api_add_action(name=k, action=step[k],
                                                                  config=config, env=env)
                for _param in res_param_arr:
                    res_param.update(_param)
            else:
                # 通过调用from_config_and_env这个类方法将ip, port, urlprefix这三个参数传入，构造完整的url
                # k=api时handler=ApiRunner, k=exec时handler=ExecRunner
                hander = self.handlers[k].from_config_and_env(config)
                res_param = hander.run(step[k])
        return res_param

