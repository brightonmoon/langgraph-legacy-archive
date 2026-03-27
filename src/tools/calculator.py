"""
계산기 Tool - 기본적인 수학 연산을 수행
"""

import ast
import operator

from langchain.tools import tool


def _safe_eval(expression: str) -> float:
    """AST를 사용한 안전한 수학 표현식 평가

    Args:
        expression: 평가할 수학 표현식

    Returns:
        계산 결과

    Raises:
        ValueError: 허용되지 않는 연산이 포함된 경우
        SyntaxError: 구문 오류가 있는 경우
    """
    # 허용된 연산자 매핑
    safe_operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
    }

    def _eval_node(node):
        """AST 노드를 재귀적으로 평가"""
        if isinstance(node, ast.Constant):
            # 숫자 상수만 허용
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"허용되지 않는 상수 타입: {type(node.value).__name__}")

        elif isinstance(node, ast.BinOp):
            # 이항 연산자
            op_type = type(node.op)
            if op_type not in safe_operators:
                raise ValueError(f"허용되지 않는 연산자: {op_type.__name__}")
            left = _eval_node(node.left)
            right = _eval_node(node.right)
            return safe_operators[op_type](left, right)

        elif isinstance(node, ast.UnaryOp):
            # 단항 연산자
            op_type = type(node.op)
            if op_type not in safe_operators:
                raise ValueError(f"허용되지 않는 단항 연산자: {op_type.__name__}")
            operand = _eval_node(node.operand)
            return safe_operators[op_type](operand)

        elif isinstance(node, ast.Expression):
            # 표현식 래퍼
            return _eval_node(node.body)

        else:
            raise ValueError(f"허용되지 않는 AST 노드: {type(node).__name__}")

    # 표현식 파싱 및 평가
    tree = ast.parse(expression, mode='eval')
    return _eval_node(tree)


@tool("calculator")
def calculator_tool(expression: str) -> str:
    """기본적인 수학 연산을 수행합니다. 사칙연산(+, -, *, /)과 거듭제곱(**)을 지원합니다.

    Args:
        expression: 계산할 수학 표현식 (예: "2 + 3 * 4")

    Returns:
        계산 결과 문자열
    """
    try:
        # 안전한 평가 수행
        result = _safe_eval(expression)

        # 결과가 너무 크거나 작은 경우 처리
        if isinstance(result, float):
            if result == float('inf') or result == float('-inf'):
                return "❌ 계산 결과가 무한대입니다."
            if result != result:  # NaN 체크
                return "❌ 계산 결과가 정의되지 않았습니다."

        return f"✅ 계산 결과: {expression} = {result}"

    except ZeroDivisionError:
        return "❌ 0으로 나눌 수 없습니다."
    except SyntaxError:
        return "❌ 수학 표현식이 올바르지 않습니다."
    except ValueError as e:
        return f"❌ {str(e)}"
    except Exception as e:
        return f"❌ 계산 중 오류 발생: {str(e)}"
