import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class SecurityLogStore:
    """
    用本地 JSON 文件模拟 security_log 表。
    """

    def __init__(self, log_file: Optional[Path] = None):
        self.log_file = log_file or Path(__file__).parent.parent / "data" / "security_log.json"
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        if not self.log_file.exists():
            self.log_file.write_text("[]", encoding="utf-8")

    def _read_all(self) -> List[Dict[str, Any]]:
        with self.log_file.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _write_all(self, records: List[Dict[str, Any]]) -> None:
        with self.log_file.open("w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

    def append(self, record: Dict[str, Any]) -> None:
        records = self._read_all()
        records.append(record)
        self._write_all(records)

    def find_by_uuid(self, request_uuid: str) -> Optional[Dict[str, Any]]:
        records = self._read_all()

        for record in reversed(records):
            if record.get("uuid") == request_uuid:
                return record

        return None

    def count_by_uuid(self, request_uuid: str) -> Optional[int]:
        records = self._read_all()

        return sum(
            1 for record in records
            if record.get("uuid") == request_uuid
        )


    def clear(self) -> None:
        """
        清空本地模拟 security_log。
        每次测试会话开始前调用，避免上一次测试的日志影响本次测试。
        """
        self._write_all([])


class LogClient:
    """
    日志查询客户端。
    """

    def __init__(self, store: Optional[SecurityLogStore] = None):
        self.store = store or SecurityLogStore()

    def search_by_uuid(self, request_uuid: str) -> Optional[Dict[str, Any]]:
        if not request_uuid:
            return None

        return self.store.find_by_uuid(request_uuid)

    def count_by_uuid(self, request_uuid: str) -> Optional[int]:
        if not request_uuid:
            return 0

        return self.store.count_by_uuid(request_uuid)