import os
import re
import time
import uuid
from client.log_client import LogClient
from typing import Any, Dict, Optional

import requests


class GatewayClient:
    """
    AI 网关接口客户端。

    职责：
    1. 管理 base_url、token、headers、timeout
    2. 封装通用 request 方法
    3. 封装手机号敏感信息检测接口
    4. 在没有真实接口环境时，支持 mock 模式，保证 demo 可执行
    """
    # 防误匹配
    PHONE_PATTERN = re.compile(r"(?<!\d)(1[3-9]\d{9})(?!\d)")

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        timeout: int = 10,
        mock: Optional[bool] = None,
    ):
        self.base_url = (base_url or os.getenv("AIGW_BASE_URL","")).rstrip("/")
        self.token = token or os.getenv("AIGW_TOKEN")
        self.timeout = timeout

        if mock is None:
            self.mock = os.getenv("AIGW_MOCK", "true").lower() == "true"
        else:
            self.mock = mock

        self.log_client = LogClient()

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "User-Agent": "aigw-pytest-demo/1.0",
            }
        )

        if self.token:
            self.session.headers.update(
                {
                    "Authorization": f"Bearer {self.token}"
                }
            )


    def request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """
        通用请求方法。
        """
        if not self.base_url:
            return{
                "status_code": None,
                "headers": {},
                "content_type": None,
                "body": None,
                "uuid": None,
                "elapsed": 0,
                "error": "base_url不能为空，请设置AIGW_BASE_URL或实例化时传入base_url"
            }

        url = f"{self.base_url}{path}"
        start_time = time.time()

        try:
            response = self.session.request(
                method=method.upper(),
                url=url,
                timeout=self.timeout,
                **kwargs,
            )
            content_type = response.headers.get("Content-Type")
            elapsed = round(time.time() - start_time, 2)
            headers =  dict(response.headers)

            try:
                if content_type and "application/json" in content_type:
                    body = response.json()
                else:
                    body = response.text
            except ValueError:
                body = {}

            return {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content_type": content_type,
                "body": body,
                "uuid": self._extract_uuid(headers, body),
                "elapsed": elapsed,
                "error": None,
            }

        except requests.exceptions.Timeout:
            elapsed = round(time.time() - start_time, 3)
            return {
                "status_code": None,
                "headers": {},
                "body": {},
                "uuid": None,
                "elapsed": elapsed,
                "error": "请求超时",
            }

        except requests.exceptions.RequestException as e:
            elapsed = round(time.time() - start_time, 3)
            return {
                "status_code": None,
                "headers": {},
                "content_type": None,
                "body": None,
                "uuid": None,
                "error": str(e),
            }

    @staticmethod
    def _extract_uuid(headers:Dict[str,Any], body:Any) -> Optional[str]:
        """
        从响应头或响应体中提取请求uuid/trace_id
        """
        possible_header_keys = [
            "uuid",
            "UUID",
            "X-Request-Id",
            "x-request-id",
            "x-trace-id",
            "X-Trace-Id",
            "Trace-Id",
            "trace-id",
        ]
        for key in possible_header_keys:
            if key in headers:
                return headers.get(key)
        if isinstance(body, dict):
            possible_body_keys = [
                "uuid",
                "request_id",
                "trace_id",
                "traceid",
                "requestId",
            ]

            for key in possible_body_keys:
                if key in body:
                    return body.get(key)
        return None


    def detect_phone_security(self, text: str) -> Dict[str, Any]:
        """
        手机号敏感信息检测,根据mock值判断本地检测还是使用接口检测

        mock=True 时，使用本地模拟检测逻辑。
        mock=False 时，请求真实网关接口。
        """
        if self.mock:
            return self._mock_detect_phone_security(text)

        response = self.request(
            method="POST",
            path="/api/v1/security/phone",
            json={"text": text},
        )

        return self._normalize_real_response(response)

    def _mock_detect_phone_security(self, text: str) -> Dict[str, Any]:
        """
        本地 mock 逻辑：
        检测文本中是否存在中国大陆手机号格式，并生成一条模拟 security_log。
        """
        request_uuid = str(uuid.uuid4())
        start_time = time.time()

        if not isinstance(text, str):
            result = {
                "status_code": 400,
                "is_sensitive": False,
                "sensitive_type": None,
                "hits": [],
                "hit_count": 0,
                "masked_text": "",
                "message": "text must be string",
                "uuid": request_uuid,
                "elapsed": round(time.time() - start_time, 3),
                "error": "text must be string",
            }

            self._write_mock_security_log(text, result)
            return result

        phones = self.PHONE_PATTERN.findall(text)

        hits = []
        masked_text = text

        for phone in phones:
            masked_phone = self._mask_phone(phone)

            hits.append(
                {
                    "type": "PHONE",
                    "value": phone,
                    "masked": masked_phone,
                }
            )

            masked_text = masked_text.replace(phone, masked_phone)

        result = {
            "status_code": 200,
            "is_sensitive": len(hits) > 0,
            "sensitive_type": "PHONE" if hits else None,
            "hits": hits,
            "hit_count": len(hits),
            "masked_text": masked_text,
            "message": "success",
            "uuid": request_uuid,
            "elapsed": round(time.time() - start_time, 3),
            "error": None,
        }

        self._write_mock_security_log(text, result)

        return result

    def _write_mock_security_log(self, text: Any, result: Dict[str, Any]) -> None:
        """
        写入一条模拟 security_log。
        """
        log_record = {
            "uuid": result.get("uuid"),
            "api": "/api/v1/security/phone",
            "request_content": text,
            "status_code": result.get("status_code"),
            "is_sensitive": result.get("is_sensitive"),
            "sensitive_type": result.get("sensitive_type"),
            "hit_count": result.get("hit_count"),
            "elapsed": result.get("elapsed"),
            "error": result.get("error"),
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        self.log_client.store.append(log_record)

    @staticmethod
    def _mask_phone(phone: str) -> str:
        """
        手机号脱敏。
        例如：13800138000 -> 138****8000
        """
        return f"{phone[:3]}****{phone[-4:]}"

    @staticmethod
    def _normalize_real_response(response: Dict[str, Any]) -> Dict[str, Any]:
        """
        真实接口响应格式适配层。

        注意：
        真实项目中需要根据后端实际返回字段调整这里。
        """
        body = response.get("body") or {}

        if not isinstance(body, dict):
            body = {}

        hits = body.get("hits", [])

        return {
            "status_code": response.get("status_code"),
            "is_sensitive": body.get("is_sensitive", False),
            "sensitive_type": body.get("sensitive_type"),
            "hits": hits,
            "hit_count": len(hits),
            "masked_text": body.get("masked_text", ""),
            "message": body.get("message"),
            "uuid": response.get("uuid"),
            "elapsed": response.get("elapsed"),
            "error": response.get("error"),
        }