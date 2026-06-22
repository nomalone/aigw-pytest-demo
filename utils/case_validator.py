
REQUIRED_MARKS = {"smoke", "regression", "security"}

def validator_case(case):
    """
    对测试用例中的字段进行验证
    """
    required_fields = [
        "case_id",
        "case_name",
        "marks",
        "request.content",
        "expect.is_sensitive",
        "expect.sensitive_type"
    ]

    for field in required_fields:
        get_nested_value(case, field)

    if not isinstance(case["marks"], list):
        raise ValueError(f"测试用例 {case['case_id']} 的 marks 必须是列表")

    for mark in case["marks"]:
        if mark not in REQUIRED_MARKS:
            raise ValueError(f"测试用例 {case['case_id']} 使用了未注册 mark：{mark}")

    return case



def get_nested_value(data,field_path):
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
        # 取下一层级继续
        current = current[key]

    return current
