"""
Math MCP Server 예제
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Math")

@mcp.tool()
def add(a: int, b: int) -> int:
    """두 숫자를 더합니다."""
    return a + b

@mcp.tool()
def multiply(a: int, b: int) -> int:
    """두 숫자를 곱합니다."""
    return a * b

@mcp.tool()
def divide(a: float, b: float) -> float:
    """첫 번째 숫자를 두 번째 숫자로 나눕니다."""
    if b == 0:
        raise ValueError("0으로 나눌 수 없습니다.")
    return a / b

@mcp.tool()
def power(base: float, exponent: float) -> float:
    """밑수를 지수만큼 거듭제곱합니다."""
    return base ** exponent

if __name__ == "__main__":
    mcp.run(transport="stdio")
