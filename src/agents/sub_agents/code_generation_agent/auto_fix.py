"""
코드 자동 수정 모듈

프로그램으로 수정 가능한 Syntax 에러를 자동으로 수정하여 LLM 호출을 최소화합니다.
"""

import ast
import re
from typing import Tuple, Optional, Dict, Any


def fix_indentation(code: str) -> str:
    """들여쓰기 오류 자동 수정
    
    Args:
        code: 수정할 코드 문자열
        
    Returns:
        수정된 코드 문자열
    """
    try:
        # 먼저 파싱 시도 - 성공하면 들여쓰기는 정상
        ast.parse(code)
        return code
    except (IndentationError, SyntaxError):
        # 들여쓰기 오류 수정 시도
        lines = code.split('\n')
        fixed_lines = []
        indent_level = 0
        prev_line_ends_with_colon = False
        
        for i, line in enumerate(lines):
            stripped = line.lstrip()
            if not stripped:
                fixed_lines.append('')
                continue
            
            # 이전 줄이 콜론으로 끝났는지 확인
            if i > 0 and fixed_lines:
                prev_line = fixed_lines[-1].rstrip()
                prev_line_ends_with_colon = prev_line.endswith(':')
            
            # 들여쓰기 레벨 조정
            if prev_line_ends_with_colon:
                # 이전 줄이 블록 시작이면 들여쓰기 증가
                indent_level += 1
            
            # 블록 종료 키워드 확인
            if stripped.startswith(('elif ', 'else:', 'except ', 'finally:')):
                # 블록 종료 후 새 블록 시작
                indent_level = max(0, indent_level - 1)
            
            # 들여쓰기 적용
            fixed_lines.append(' ' * (indent_level * 4) + stripped)
            
            # 다음 줄을 위한 들여쓰기 레벨 조정
            if stripped.endswith(':'):
                # 블록 시작
                pass  # 다음 줄에서 증가
            elif stripped.startswith(('return', 'break', 'continue', 'pass', 'raise')):
                # 블록 내부 명령어
                pass
            else:
                # 일반 코드 - 블록 종료 가능성 확인
                if not prev_line_ends_with_colon:
                    # 이전 줄이 블록 시작이 아니면 들여쓰기 유지
                    pass
        
        return '\n'.join(fixed_lines)
    except Exception:
        return code  # 수정 실패 시 원본 반환


def fix_brackets(code: str) -> str:
    """괄호 불일치 자동 수정
    
    Args:
        code: 수정할 코드 문자열
        
    Returns:
        수정된 코드 문자열
    """
    brackets = {'(': ')', '[': ']', '{': '}'}
    lines = code.split('\n')
    fixed_lines = lines.copy()
    
    # 각 줄에서 괄호 매칭 확인
    for i, line in enumerate(lines):
        stack = []
        fixed_line = list(line)
        
        for j, char in enumerate(line):
            if char in brackets:
                stack.append((j, char))
            elif char in brackets.values():
                if stack:
                    open_idx, open_char = stack.pop()
                    if brackets[open_char] != char:
                        # 괄호 타입 불일치 - 수정
                        fixed_line[j] = brackets[open_char]
                else:
                    # 닫는 괄호가 열리는 괄호 없음 - 제거
                    fixed_line[j] = ''
        
        # 남은 열린 괄호 닫기
        while stack:
            open_idx, open_char = stack.pop()
            fixed_line.append(brackets[open_char])
        
        fixed_lines[i] = ''.join(fixed_line)
    
    return '\n'.join(fixed_lines)


def fix_basic_syntax(code: str) -> str:
    """기본 문법 오류 자동 수정
    
    Args:
        code: 수정할 코드 문자열
        
    Returns:
        수정된 코드 문자열
    """
    lines = code.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        fixed_line = line
        
        # 콜론 누락 수정 (if, for, while, def, class 뒤)
        if re.search(r'\b(if|elif|for|while|def|class|try|except|finally)\s+[^:]+$', line):
            if not line.rstrip().endswith(':'):
                fixed_line = line.rstrip() + ':'
        
        # 들여쓰기 후 콜론 누락 (이미 들여쓰기가 있는 경우)
        if re.search(r'^\s+(if|elif|for|while|def|class|try|except|finally)\s+[^:]+$', line):
            if not line.rstrip().endswith(':'):
                fixed_line = line.rstrip() + ':'
        
        fixed_lines.append(fixed_line)
    
    return '\n'.join(fixed_lines)


def fix_undefined_variables(code: str, context: Optional[Dict[str, Any]] = None) -> str:
    """정의되지 않은 변수 자동 수정 (제한적, CSV 분석 도메인 특화)
    
    Args:
        code: 수정할 코드 문자열
        context: 컨텍스트 정보 (domain, csv_file_path 등)
        
    Returns:
        수정된 코드 문자열
    """
    try:
        tree = ast.parse(code)
        defined_vars = set()
        used_vars = set()
        
        # 변수 정의 수집
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        defined_vars.add(target.id)
        
        # 변수 사용 수집
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                # 내장 함수/상수 제외
                if node.id not in dir(__builtins__):
                    used_vars.add(node.id)
        
        # 정의되지 않은 변수 찾기
        undefined_vars = used_vars - defined_vars
        
        # CSV 분석 도메인 특화: filepath 변수 자동 추가
        if context and context.get("domain") == "csv_analysis":
            filepath_vars = {var for var in undefined_vars if var.startswith('filepath')}
            if filepath_vars:
                csv_file_path = context.get("csv_file_path", "")
                csv_file_paths = context.get("csv_file_paths", [])
                
                var_definitions = []
                if csv_file_paths and len(csv_file_paths) > 1:
                    # 여러 파일 모드
                    for i, path in enumerate(csv_file_paths):
                        var_name = 'filepath' if i == 0 else f'filepath_{i+1}'
                        if var_name in filepath_vars:
                            var_definitions.append(f'{var_name} = "{path}"')
                elif csv_file_path:
                    # 단일 파일 모드
                    if 'filepath' in filepath_vars:
                        var_definitions.append(f'filepath = "{csv_file_path}"')
                
                if var_definitions:
                    # 변수 정의를 코드 앞에 추가
                    code = '\n'.join(var_definitions) + '\n' + code
        
        return code
    except Exception:
        return code  # 파싱 실패 시 원본 반환


def auto_fix_syntax_errors(
    code: str,
    syntax_error: SyntaxError,
    context: Optional[Dict[str, Any]] = None
) -> Tuple[str, bool]:
    """Syntax 에러 자동 수정 시도
    
    Args:
        code: 수정할 코드 문자열
        syntax_error: 발견된 SyntaxError 객체
        context: 컨텍스트 정보
        
    Returns:
        (수정된 코드, 성공 여부)
    """
    error_type = syntax_error.msg.lower()
    fixed_code = code
    
    # 1. 들여쓰기 오류
    if 'indentation' in error_type or 'unexpected indent' in error_type:
        print("  🔧 들여쓰기 오류 자동 수정 시도...")
        fixed_code = fix_indentation(fixed_code)
        try:
            ast.parse(fixed_code)
            print("  ✅ 들여쓰기 오류 자동 수정 성공!")
            return fixed_code, True
        except SyntaxError:
            pass
    
    # 2. 괄호 불일치
    if 'unmatched' in error_type or 'unclosed' in error_type or 'unterminated' in error_type:
        print("  🔧 괄호 불일치 자동 수정 시도...")
        fixed_code = fix_brackets(fixed_code)
        try:
            ast.parse(fixed_code)
            print("  ✅ 괄호 불일치 자동 수정 성공!")
            return fixed_code, True
        except SyntaxError:
            pass
    
    # 3. 기본 문법 오류 (콜론 누락 등)
    if 'invalid syntax' in error_type or 'expected' in error_type:
        print("  🔧 기본 문법 오류 자동 수정 시도...")
        fixed_code = fix_basic_syntax(fixed_code)
        try:
            ast.parse(fixed_code)
            print("  ✅ 기본 문법 오류 자동 수정 성공!")
            return fixed_code, True
        except SyntaxError:
            pass
    
    # 4. 변수명 오류 (제한적, CSV 분석 도메인 특화)
    if 'name' in error_type and ('not defined' in error_type or 'is not defined' in error_type):
        print("  🔧 변수명 오류 자동 수정 시도...")
        fixed_code = fix_undefined_variables(fixed_code, context)
        try:
            ast.parse(fixed_code)
            print("  ✅ 변수명 오류 자동 수정 성공!")
            return fixed_code, True
        except SyntaxError:
            pass
    
    return code, False  # 수정 실패

