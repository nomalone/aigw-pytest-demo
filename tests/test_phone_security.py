import json
from pathlib import Path

import allure
import pytest

from client.gateway_client import GatewayClient
from client.log_client import LogClient
from utils.wait import wait_log


REQUIRED_MARKS = {"smoke", "regression", "security"}


def get_nested_value(data, field_path):
    """
    根据类似 request.content 的路径读取嵌套字段。

    如果字段不存在，直接抛出清晰错误。
    """
    current = data

    for key in field_path.split("."):
        if not isinstance(current, dict) or key not in current:
            raise ValueError(
                f"测试用例缺少必填字段：{field_path}，"
                f"当前用例：{data.get('case_id', 'UNKNOWN')}"
            )

        current = current[key]

    return current


def validate_case(case):
    """
    校验 JSON 测试用例字段。
    """
    required_fields = [
        "case_id",
        "case_name",
        "request.content",
        "expect.is_sensitive",
        "expect.sensitive_type",
        "marks",
    ]

    for field in required_fields:
        get_nested_value(case, field)

    if not isinstance(case["marks"], list):
        raise ValueError(f"测试用例 {case['case_id']} 的 marks 必须是列表")

    for mark in case["marks"]:
        if mark not in REQUIRED_MARKS:
            raise ValueError(f"测试用例 {case['case_id']} 使用了未注册 mark：{mark}")

    return case


def load_phone_cases():
    """
    读取并校验手机号敏感信息检测测试数据。
    """
    case_file = Path(__file__).parent.parent / "data" / "phone_cases.json"

    with case_file.open("r", encoding="utf-8") as f:
        cases = json.load(f)

    return [validate_case(case) for case in cases]


def build_case_params():
    """
    将 JSON 中的 marks 转换成 pytest mark。
    """
    mark_map = {
        "smoke": pytest.mark.smoke,
        "regression": pytest.mark.regression,
        "security": pytest.mark.security,
    }

    params = []

    for case in load_phone_cases():
        case_marks = [mark_map[mark_name] for mark_name in case["marks"]]

        params.append(
            pytest.param(
                case,
                marks=case_marks,
                id=case["case_id"],
            )
        )

    return params


@pytest.fixture(scope="session")
def gateway_client():
    """
    创建 GatewayClient 对象。
    """
    return GatewayClient()


@pytest.fixture(scope="session")
def log_client():
    """
    创建日志查询客户端。
    每次测试会话开始前，清空本地模拟日志。
    """
    client = LogClient()
    client.store.clear()
    return client


@allure.feature("安全检测模块")
@allure.story("手机号敏感信息检测")
@pytest.mark.parametrize("case", build_case_params())
def test_phone_sensitive_detection(gateway_client, log_client, case):
    """
    手机号敏感信息检测测试。
    """
    allure.dynamic.title(case["case_name"])

    with allure.step("读取测试输入和预期结果"):
        text = case["request"]["content"]
        expected = case["expect"]

    with allure.step("调用手机号敏感信息检测接口"):
        result = gateway_client.detect_phone_security(text)

    with allure.step("断言接口基础返回"):
        assert result["status_code"] == expected.get("status_code", 200)
        assert result["uuid"]
        assert isinstance(result["elapsed"], float)
        assert result["error"] is None

    with allure.step("断言是否识别为敏感信息"):
        assert result["is_sensitive"] == expected["is_sensitive"]

    with allure.step("断言敏感信息类型"):
        assert result["sensitive_type"] == expected["sensitive_type"]

    with allure.step("断言命中数量"):
        assert result["hit_count"] == expected.get("hit_count", result["hit_count"])

    with allure.step("断言脱敏文本内容"):
        assert expected.get("masked_text_contains", "") in result["masked_text"]

    with allure.step("根据 uuid 轮询等待 security_log 日志出现"):
        log = wait_log(log_client, result["uuid"], timeout=3, interval=0.2)

        assert log is not None, f"未查询到 uuid={result['uuid']} 对应的 security_log"
        assert log["uuid"] == result["uuid"]
        assert log["request_content"] == text
        assert log["is_sensitive"] == expected["is_sensitive"]
        assert log["sensitive_type"] == expected["sensitive_type"]