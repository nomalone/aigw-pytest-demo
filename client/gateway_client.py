import os
import re
import time
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
            raise ValueError("base_url 不能为空，请设置 AIGW_BASE_URL 或实例化时传入 base_url")

        url = f"{self.base_url}{path}"

        start_time = time.time()
        try:
            response = self.session.request(
                method=method.upper(),
                url=url,
                timeout=self.timeout,
                **kwargs,
            )
            cost_time = round(time.time() - start_time, 3)
            content_type = response.headers.get("Content-Type")

            try:
                if "application/json" in content_type:
                    body = response.json()
                else:
                    body = response.text
            except ValueError:
                body = {}

            return {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": body,
                "text": response.text,
                "error": None,
            }

        except requests.exceptions.Timeout:
            cost_time = round(time.time() - start_time, 3)
            return {
                "status_code": None,
                "headers": {},
                "body": {},
                "text": "",
                "cost_time": cost_time,
                "error": "请求超时",
            }

        except requests.exceptions.RequestException as e:
            return {
                "status_code": None,
                "headers": {},
                "body": {},
                "text": "",
                "error": str(e),
            }

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
        检测文本中是否存在中国大陆手机号格式。
        """
        if not isinstance(text, str):
            return {
                "status_code": 400,
                "is_sensitive": False,
                "sensitive_type": None,
                "hits": [],
                "hit_count": 0,
                "masked_text": "",
                "message": "text must be string",
            }
        # 将匹配正则表达式的手机号放进列表中
        phones = self.PHONE_PATTERN.findall(text)

        hits = []
        masked_text = text

       #对号码以及原内容进行加工处理
        for phone in phones:
            masked_phone = self._mask_phone(phone)
            hits.append(
                {
                    "type": "PHONE",
                    "value": phone,
                    "masked": masked_phone,
                }
            )
            masked_text = masked_text.replace(phone,masked_phone)

        return {
            "status_code": 200,
            "is_sensitive": len(hits) > 0,
            "sensitive_type": "PHONE" if hits else None,
            "hits": hits,
            "hit_count": len(hits),
            "masked_text": masked_text,
            "message": "success",
        }

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

        真实项目中需要根据后端实际返回字段调整这里。
        """
        body = response.get("body", {})

        return {
            "status_code": response.get("status_code"),
            "is_sensitive": body.get("is_sensitive", False),
            "sensitive_type": body.get("sensitive_type"),
            "hits": body.get("hits", []),
            "hit_count": len(body.get("hits", [])),
            "masked_text": body.get("masked_text", ""),
            "message": body.get("message"),
            "error": response.get("error"),
        }