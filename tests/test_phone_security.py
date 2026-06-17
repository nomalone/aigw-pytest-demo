import json
from pathlib import Path

import allure
import pytest

from client.gateway_client import GatewayClient


def load_phone_cases():
    """
    读取手机号敏感信息检测测试数据。
    """
    case_file = Path(__file__).parent.parent / "data" / "phone_cases.json"

    with case_file.open("r", encoding="utf-8") as f:
        return json.load(f)


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
        case_marks = []
        for mark_name in case.get("marks", []):
            if mark_name in mark_map:
                case_marks.append(mark_map[mark_name])
        params.append(
            pytest.param(
                case,
                marks = case_marks,
                id = case["case_id"],
            )
        )

    return params


@pytest.fixture(scope="session")
def gateway_client():
    """
    创建 GatewayClient 对象。
    scope=session 表示整个测试会话只创建一次。
    """
    return GatewayClient()


@allure.feature("安全检测模块")
@allure.story("手机号敏感信息检测")
@pytest.mark.parametrize("case", build_case_params())
def test_phone_sensitive_detection(gateway_client, case):
    """
    手机号敏感信息检测测试。
    """
    allure.dynamic.title(case["title"])

    with allure.step("读取测试输入和预期结果"):
        text = case["text"]
        expected = case["expected"]

    with allure.step("调用手机号敏感信息检测接口"):
        result = gateway_client.detect_phone_security(text)

    with allure.step("断言接口状态码"):
        assert result["status_code"] == expected["status_code"]

    with allure.step("断言是否识别为敏感信息"):
        assert result["is_sensitive"] == expected["is_sensitive"]

    with allure.step("断言敏感信息类型"):
        assert result["sensitive_type"] == expected["sensitive_type"]

    with allure.step("断言命中数量"):
        assert result["hit_count"] == expected["hit_count"]

    with allure.step("断言脱敏文本内容"):
        assert expected["masked_text_contains"] in result["masked_text"]