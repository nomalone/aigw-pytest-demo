import json
from pathlib import Path

import allure
import pytest
from allure_commons.types import AttachmentType

from client.gateway_client import GatewayClient
from client.log_client import LogClient
from utils.case_loader import build_case_params
from utils.wait import wait_log


REQUIRED_MARKS = {"smoke", "regression", "security"}



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


def attach_debug_info(case_name, uuid, request_body, response_body, log_count = None):
    debug_info = {
        "case_name": case_name,
        "uuid": uuid,
        "request_body": request_body,
        "response_body": response_body,
        "log_count": log_count
    }
    allure.attach(
        json.dumps(debug_info, ensure_ascii = False, indent = 2),
        name = "debug_info",
        attachment_type=allure.attachment_type.JSON,
    )


@allure.feature("安全检测模块")
@allure.story("手机号敏感信息检测")
@pytest.mark.parametrize("case", build_case_params())
def test_phone_sensitive_detection(gateway_client, log_client, case):
    """
    手机号敏感信息检测测试。
    """
    allure.dynamic.title(case["case_name"])

    with allure.step("准备测试数据"):
        case_name = case["case_name"]
        text = case["request"]["content"]
        expected = case["expect"]
        request_body = {"text": text}


    with allure.step("调用手机号敏感信息检测接口"):
        result = gateway_client.detect_phone_security(text)
        uuid = result.get("uuid")
        response_body = result

        attach_debug_info(
            case_name=case_name,
            uuid=uuid,
            request_body=request_body,
            response_body=response_body,
        )

    with allure.step("断言接口基础返回"):
        assert result["status_code"] == expected.get("status_code", 200)
        assert result["uuid"]
        assert isinstance(result["elapsed"], float)
        assert result["error"] is None

    with allure.step("校验敏感识别信息"):
        assert result["is_sensitive"] == expected["is_sensitive"]
        assert result["sensitive_type"] == expected["sensitive_type"]
        assert result["hit_count"] == expected.get("hit_count", result["hit_count"])

    with allure.step("断言脱敏文本内容"):
        assert expected.get("masked_text_contains", "") in result["masked_text"]

    with allure.step("根据 uuid 轮询等待 security_log 日志出现"):
        log = wait_log(log_client, result["uuid"], timeout=3, interval=0.2)
        log_count = log_client.count_by_uuid(result["uuid"])
        attach_debug_info(
            case_name=case_name,
            uuid=result["uuid"],
            request_body=request_body,
            response_body=response_body,
            log_count=log_count
        )