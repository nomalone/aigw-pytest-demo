import time
from typing import Callable, Any, Optional


def wait_util(
        condition: Callable[[],Any],
        timeout: float = 5,
        interval: float = 0.5,
) -> Optional[Any]:
    """
    轮询等待某个条件成立

    condition 返回真值时立刻返回该结果
    超过时返回None
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        result = condition()

        if result:
            return result

        time.sleep(interval)

    return None

def wait_log(log_client, request_uuid:str, timeout: float = 5, interval: float = 0.5):
    """
    等待指定uuid的日志出现
    """
    return wait_util(
        condition=lambda: log_client.search_by_uuid(request_uuid),
        timeout=timeout,
        interval=interval,
    )
