import json
import warnings
import urllib3
from pathlib import Path
# from .common import getcwd
from pytest_api.common import getcwd
from requests import Request, Session

# 忽略告警信息
warnings.filterwarnings("ignore")
urllib3.disable_warnings()


class ApiRequest:
    '''
    request操作的封装
    '''

    def __init__(self, ip, port=80, urlprefix=""):
        self.ip = ip
        self.port = port
        self.headers = None
        self.proto = "https"
        self.s = Session()
        # url前缀
        self.urlprefix = urlprefix
        self.auth = None
        self.url = ""

    def _url(self, url):
        self.url = f'{self.proto}://{self.ip}:{self.port}{self.urlprefix}' \
                   f'{url}'

    # 私有函数，内部使用
    def _filter_auth(self, kw):
        """
        可在单个步骤删除全局授权信息
        只要带的形式是
        auth: none
        """
        auth = self.auth
        if "auth" in kw:
            if kw["auth"] == 'none':
                auth = None
            else:
                auth = tuple(kw["auth"])
        return auth

    # 私有函数，内部使用
    def _filter_headers(self, kw):
        """
        可在单个步骤删除全局授权信息
        只要带的形式是
        header: none
        """
        headers = self.headers
        if "headers" in kw:
            if kw["headers"] == 'none':
                headers = None
            else:
                headers = kw["headers"]
        return headers

    def handle_files(self, kw):
        """
        发送文件的操作逻辑
        其中传输过来的files的结构是：
        {
            request:
                url: "",
                files: {
                    "file": "case_data/ssl/ssl.cert"
                    # 其中key值中的file需要填写的文件上传字段
                    # 其中的file不是固定写死的，是具体API定义的文件字段名称
                    # 多个文件也类似这样写
                }
        }
        """
        _files = None if "files" not in kw else kw["files"]
        if _files:
            files = {}
            cur_work_path = getcwd()
            for file_key, filepath in _files.items():
                filepath = Path(cur_work_path) / Path(filepath)
                files[file_key] = open(filepath, 'rb')
            return files
        return None

    def handle_urlprefix(self, kw):
        """
        处理url前缀问题，有的步骤不需要url前缀，需要卸载掉
        """
        if "urlprefix" in kw:
            if kw["urlprefix"] == 'none':
                self.urlprefix = ""
            else:
                self.urlprefix = kw["urlprefix"]

    def send(self, **kw):
        method = None if "method" not in kw else kw["method"]
        url = None if "url" not in kw else kw["url"]
        files = self.handle_files(kw)
        data = None if "data" not in kw else kw["data"]
        # json = None if "json" not in kw else kw["json"]
        params = None if "params" not in kw else kw["params"]
        timeout = 20 if "timeout" not in kw else kw["timeout"]
        auth = self._filter_auth(kw)
        headers = self._filter_headers(kw)
        self.handle_urlprefix(kw)

        if data and isinstance(data, dict):
            data = json.dumps(kw["data"], ensure_ascii=False).encode("utf-8")

        # 避免json中文问题，因为默认requests库的json是ascii编码
        # 改成自己组装，并变成data方式发送
        if "json" in kw:
            if not headers:
                headers = {}
            if "Content-Type" not in headers:
                headers["Content-Type"] = "application/json"
            if "headers" in kw and kw["headers"] == 'none':
                headers = None
            data = json.dumps(kw["json"], ensure_ascii=False).encode("utf-8")

        if headers and "Cookie" in headers:
            # 避免cookie和auth共存的行为
            auth = None

        self._url(url)
        r = Request(
            method=method.upper(),
            url=self.url,
            headers=headers,
            files=files,
            data=data,
            json=None,
            params=params,
            auth=auth,
        )
        prepped = r.prepare()
        # prepped = self.s.prepare_request(r)
        res = self.s.send(prepped, verify=False, timeout=timeout)
        return res