def pytest_api_add_action(name, action, config, env):
    """pytest api框架步骤中增加一个动作处理支持，
    name是动作的名称，当前内置了api和exec两个动作
    其中action是一个字典结构，存储的是该动作的所有信息
    config存储的是pytest的config对象信息，
    envs是环境变量信息，可以根据envs得到urlprefix，proto，headers等信息，也包括授权信息
    如果要返回变量，则返回的形式是一个字段

    return {
        "var1" : 1,
        "var2": "test"
    }
    """
