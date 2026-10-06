"""基于 AST 白名单的无 eval 计算器。"""

from __future__ import annotations

import ast
import math
import operator
from typing import Callable


_BINARY: dict[type[ast.operator], Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCTIONS = {"abs": abs, "round": round, "sqrt": math.sqrt, "min": min, "max": max}
_CONSTANTS = {"pi": math.pi, "e": math.e}


def calculate(expression: str) -> int | float:
    value = expression.strip()
    if not value or len(value) > 200:
        raise ValueError("表达式必须为 1～200 个字符。")
    try:
        tree = ast.parse(value, mode="eval")
    except SyntaxError as exc:
        raise ValueError("数学表达式格式错误。") from exc
    result = _evaluate(tree.body, 0)
    if isinstance(result, bool) or not isinstance(result, (int, float)):
        raise ValueError("表达式结果不是数字。")
    if not math.isfinite(float(result)) or abs(float(result)) > 1e100:
        raise ValueError("计算结果过大或不是有限数。")
    return result


def _evaluate(node: ast.AST, depth: int) -> int | float:
    if depth > 20:
        raise ValueError("表达式嵌套过深。")
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.Name) and node.id in _CONSTANTS:
        return _CONSTANTS[node.id]
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_evaluate(node.operand, depth + 1))
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
        left = _evaluate(node.left, depth + 1)
        right = _evaluate(node.right, depth + 1)
        if isinstance(node.op, ast.Pow) and abs(float(right)) > 100:
            raise ValueError("指数绝对值不能超过 100。")
        try:
            return _BINARY[type(node.op)](left, right)
        except (ArithmeticError, ValueError) as exc:
            raise ValueError(f"无法计算：{exc}") from exc
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCTIONS:
        if node.keywords or len(node.args) > 10:
            raise ValueError("函数参数不合法。")
        args = [_evaluate(arg, depth + 1) for arg in node.args]
        try:
            return _FUNCTIONS[node.func.id](*args)
        except (ArithmeticError, TypeError, ValueError) as exc:
            raise ValueError(f"无法计算：{exc}") from exc
    raise ValueError("表达式包含不允许的操作。")

