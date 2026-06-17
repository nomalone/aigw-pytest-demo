# aigw-pytest-demo

## 项目简介

本项目是一个基于 pytest 的接口自动化测试 demo，主要用于测试 AI 网关中的手机号敏感信息检测模块。

项目通过 `GatewayClient` 封装接口请求，通过 `phone_cases.json` 管理测试数据，通过 `pytest.mark.parametrize` 实现数据驱动测试，并支持 smoke、regression、security 等测试分类执行。

## 测试模块

当前 demo 主要覆盖：

* 手机号敏感信息识别
* 多手机号识别
* 无手机号文本识别
* 非法手机号前缀校验
* 位数不足号码校验
* 长数字中手机号误识别校验
* 手机号脱敏结果校验

## 项目结构

```text
aigw-pytest-demo/
├── client/
│   ├── __init__.py
│   └── gateway_client.py
├── data/
│   └── phone_cases.json
├── tests/
│   └── test_phone_security.py
├── pytest.ini
├── requirements.txt
└── README.md
```

## 环境准备

安装依赖：

```bash
pip install -r requirements.txt
```

如果下载较慢，可以使用国内镜像源：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 执行全部测试

```bash
pytest
```

## 执行冒烟测试

```bash
pytest -m smoke
```

## 执行回归测试

```bash
pytest -m regression
```

## 执行安全测试

```bash
pytest -m security
```

## 生成 Allure 报告

```bash
pytest --alluredir=allure-results --clean-alluredir
allure serve allure-results
```

## mock 模式说明

本项目默认开启 mock 模式，即不依赖真实接口环境也可以运行测试。

默认配置：

```bash
AIGW_MOCK=true
```

如果需要连接真实 AI 网关接口，可以设置：

```bash
AIGW_MOCK=false
AIGW_BASE_URL=http://your-gateway-host
AIGW_TOKEN=your-token
```

然后根据真实接口返回格式，调整 `GatewayClient._normalize_real_response` 方法。

## 用例设计说明

测试数据存放在：

```text
data/phone_cases.json
```

每条 case 包含：

* case_id：用例编号
* title：用例标题
* marks：用例分类
* text：输入文本
* expected：预期结果

示例：

```json
{
  "case_id": "phone_plain",
  "title": "文本中包含一个完整手机号",
  "marks": ["smoke", "security"],
  "text": "用户反馈：我的手机号是13800138000，请尽快联系。",
  "expected": {
    "status_code": 200,
    "is_sensitive": true,
    "sensitive_type": "PHONE",
    "hit_count": 1,
    "masked_text_contains": "138****8000"
  }
}
```

## 项目特点

* 使用 pytest 作为测试框架
* 使用 requests 封装接口请求
* 使用 JSON 文件实现数据驱动
* 使用 pytest fixture 管理客户端对象
* 使用 pytest mark 实现测试分类
* 使用 Allure 生成可视化测试报告
* 支持 mock 模式，方便本地学习和演示
