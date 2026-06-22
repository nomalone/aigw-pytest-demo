import json
from pathlib import Path

import pytest

from utils.case_validator import validator_case


def load_phone_cases():
    """
    读取测试用例并对每条用例进行参数验证
    :return:
    """
    case_file = Path(__file__).parent.parent / 'data' / 'phone_cases.json'
    with case_file.open("r", encoding="utf-8") as f:
        cases = json.load(f)

    return [validator_case(case) for case in cases]

def build_case_params():
    """
    将测试用例中的marks转化为pytest mark
    :return:
    """
    mark_map = {
        "security": pytest.mark.security,
        "smoke": pytest.mark.smoke,
        "regression": pytest.mark.regression,
    }

    params = []
    for case in load_phone_cases():
        case_marks = [mark_map[mark_name] for mark_name in case["marks"]]

        params.append(
            pytest.param(
                case,
                marks = case_marks,
                id = case["case_id"]
            )
        )

    return params
