"""
코드 전처리 유틸리티

생성된 코드를 실행 가능하도록 전처리하는 함수들을 제공합니다.
- 파일 경로 변수 추가
- 데이터 타입 전처리 코드 추가
- 호스트 경로를 도커 경로로 변환
"""

import re
from pathlib import Path
from typing import List, Optional


def add_data_type_preprocessing(code: str) -> str:
    """데이터 타입 확인 및 전처리 코드 추가
    
    수치형 분석 함수(corr, describe 등) 사용 시 문자열 컬럼으로 인한 에러를 방지하기 위해
    자동으로 데이터 타입 확인 및 전처리 코드를 추가합니다.
    
    Args:
        code: 생성된 코드
        
    Returns:
        데이터 타입 전처리 코드가 추가된 코드
    """
    # 수치형 분석 함수가 있는지 확인
    numeric_analysis_functions = [
        r'\.corr\(',
        r'\.describe\(',
        r'\.cov\(',
        r'\.corrwith\(',
        r'np\.corrcoef\(',
        r'np\.correlate\(',
    ]
    
    has_numeric_analysis = any(re.search(pattern, code) for pattern in numeric_analysis_functions)
    
    # DataFrame 변수명 찾기 (df, data, df1 등)
    df_variable_pattern = r'(df\d*|data\d*)\s*='
    df_matches = re.findall(df_variable_pattern, code)
    df_var = df_matches[0] if df_matches else 'df'
    
    # pd.read_csv 후에 데이터 타입 확인 코드가 이미 있는지 확인
    has_type_check = re.search(r'select_dtypes|dtypes|\.dtype', code)
    
    # 수치형 분석 함수가 있고, 타입 확인 코드가 없으면 추가
    if has_numeric_analysis and not has_type_check:
        # pd.read_csv 다음에 데이터 타입 확인 및 전처리 코드 추가
        read_csv_pattern = rf'({df_var}\s*=\s*pd\.read_csv\([^)]+\))'
        
        preprocessing_code = f"""
# 데이터 타입 확인 및 전처리 (자동 추가)
# 수치형 분석을 위해 수치형 컬럼만 선택
if '{df_var}' in locals() or '{df_var}' in globals():
    {df_var}_numeric = {df_var}.select_dtypes(include=['int64', 'float64', 'int32', 'float32'])
    {df_var}_non_numeric = {df_var}.select_dtypes(exclude=['int64', 'float64', 'int32', 'float32'])
    
    # 비수치형 컬럼 확인 (DataFrame인지 확인)
    if hasattr({df_var}_non_numeric, 'columns') and len({df_var}_non_numeric.columns) > 0:
        non_numeric_cols = list({df_var}_non_numeric.columns)
        print(f"⚠️ 비수치형 컬럼 발견: {{non_numeric_cols}}")
        print(f"   수치형 분석에는 수치형 컬럼만 사용됩니다.")
    
    # 수치형 컬럼이 있으면 수치형 데이터프레임 사용
    if hasattr({df_var}_numeric, 'columns') and len({df_var}_numeric.columns) > 0:
        {df_var} = {df_var}_numeric
        numeric_cols = list({df_var}.columns)
        print(f"✅ 수치형 컬럼 {{len(numeric_cols)}}개 선택: {{numeric_cols}}")
    else:
        print("⚠️ 경고: 수치형 컬럼이 없습니다.")
"""
        
        # pd.read_csv 다음에 전처리 코드 추가
        if re.search(read_csv_pattern, code):
            code = re.sub(
                read_csv_pattern,
                rf'\1{preprocessing_code}',
                code
            )
            print("✅ 데이터 타입 전처리 코드 추가 (수치형 분석 함수 사용 감지)")
        else:
            # pd.read_csv를 찾지 못한 경우, 첫 번째 DataFrame 할당 다음에 추가
            first_df_assignment = re.search(rf'{df_var}\s*=\s*[^\n]+', code)
            if first_df_assignment:
                insert_pos = first_df_assignment.end()
                code = code[:insert_pos] + preprocessing_code + code[insert_pos:]
                print("✅ 데이터 타입 전처리 코드 추가 (DataFrame 할당 후)")
    
    return code


def add_csv_filepath_variables(
    code: str,
    csv_file_path: Optional[str] = None,
    csv_file_paths: Optional[List[str]] = None
) -> str:
    """CSV 파일 경로 변수를 코드에 추가
    
    Args:
        code: 생성된 코드
        csv_file_path: 단일 CSV 파일 경로 (하위 호환성)
        csv_file_paths: CSV 파일 경로 목록
        
    Returns:
        파일 경로 변수가 추가된 코드
    """
    # 여러 파일 모드
    if csv_file_paths and len(csv_file_paths) > 1:
        # 여러 파일 경로 변수가 있는지 확인
        has_filepath_vars = any(
            f'filepath_{i+1}' in code or (i == 0 and 'filepath' in code)
            for i in range(len(csv_file_paths))
        )
        
        if not has_filepath_vars:
            # 여러 파일 경로 변수 추가
            filepath_vars = []
            for i, file_path in enumerate(csv_file_paths):
                var_name = 'filepath' if i == 0 else f'filepath_{i+1}'
                filepath_vars.append(f'{var_name} = "{file_path}"')
            code = '\n'.join(filepath_vars) + '\n' + code
    else:
        # 단일 파일 모드 (하위 호환성)
        file_path = csv_file_paths[0] if csv_file_paths else csv_file_path
        if not file_path:
            return code
        
        # 파일 경로에서 파일명 추출
        file_path_obj = Path(file_path)
        file_name = file_path_obj.name
        
        # filepath 변수가 없고 pd.read_csv가 있는 경우 처리
        if 'filepath' not in code and 'pd.read_csv' in code:
            # pd.read_csv에 직접 경로가 있는 경우 변수로 변경
            # 패턴 1: pd.read_csv("전체경로") 또는 pd.read_csv('전체경로')
            pattern_full_path = r"pd\.read_csv\(['\"]([^'\"]+)['\"]"
            matches = re.findall(pattern_full_path, code)
            
            # 패턴 2: pd.read_csv("파일명만") - 파일명만 있는 경우
            pattern_filename_only = rf"pd\.read_csv\(['\"]{re.escape(file_name)}['\"]"
            
            # 파일명만 있는 경우 처리
            if re.search(pattern_filename_only, code):
                # 원본 경로 사용 (execute_code_node에서 도커 경로로 변환)
                code = f'filepath = "{file_path}"\n' + code
                code = re.sub(pattern_filename_only, 'pd.read_csv(filepath)', code)
                print(f"✅ 파일명만 있는 패턴을 filepath 변수로 교체: {file_name}")
            # 전체 경로가 있는 경우 처리
            elif matches:
                # 원본 경로 사용 (execute_code_node에서 도커 경로로 변환)
                code = f'filepath = "{file_path}"\n' + code
                code = re.sub(pattern_full_path, 'pd.read_csv(filepath)', code)
                print(f"✅ 전체 경로 패턴을 filepath 변수로 교체")
    
    return code


def convert_host_paths_to_docker_paths(
    code: str,
    csv_file_path: Optional[str] = None,
    csv_file_paths: Optional[List[str]] = None
) -> str:
    """코드에서 호스트 경로를 도커 경로로 변환
    
    코딩 에이전트가 생성한 코드에 호스트 경로가 포함된 경우 도커 경로로 변환합니다.
    
    Args:
        code: 변환할 코드 문자열
        csv_file_path: 단일 CSV 파일 경로
        csv_file_paths: CSV 파일 경로 목록
        
    Returns:
        도커 경로로 변환된 코드
    """
    # 변환할 파일 경로 목록
    files_to_convert = csv_file_paths if csv_file_paths else ([csv_file_path] if csv_file_path else [])
    
    if not files_to_convert:
        return code
    
    # 각 파일에 대해 호스트 경로를 도커 경로로 변환
    for i, file_path in enumerate(files_to_convert):
        if not file_path:
            continue
        
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            continue
        
        # 호스트 절대 경로
        host_path = str(file_path_obj.resolve())
        file_name = file_path_obj.name
        
        # 도커 경로 결정
        # 코드 파일과 같은 디렉토리면 /workspace/code/, 아니면 /workspace/data/
        # 간단하게 data 디렉토리로 가정 (실제로는 execute_code_node에서 정확히 결정됨)
        docker_path = f"/workspace/data/{file_name}"
        
        # 상대 경로 패턴 (data/파일명, ./data/파일명 등)
        relative_patterns = []
        if "data/" in file_path or file_path.startswith("data/"):
            relative_patterns.append((rf'["\']data/{re.escape(file_name)}["\']', f'"{docker_path}"'))
            relative_patterns.append((rf'["\']\./data/{re.escape(file_name)}["\']', f'"{docker_path}"'))
        
        # 코드에서 호스트 경로를 찾아서 도커 경로로 변환
        # 패턴: "경로" 또는 '경로' 형식
        patterns = [
            (rf'["\']{re.escape(host_path)}["\']', f'"{docker_path}"'),
            (rf'["\']{re.escape(file_path)}["\']', f'"{docker_path}"'),
            # 변수 할당 패턴: filepath = "경로"
            (rf'(filepath(?:_\d+)?)\s*=\s*["\']{re.escape(host_path)}["\']', rf'\1 = "{docker_path}"'),
            (rf'(filepath(?:_\d+)?)\s*=\s*["\']{re.escape(file_path)}["\']', rf'\1 = "{docker_path}"'),
        ]
        
        # 상대 경로 패턴 추가
        patterns.extend(relative_patterns)
        
        for pattern, replacement in patterns:
            code = re.sub(pattern, replacement, code)
    
    return code


def prepare_code_for_execution(
    code: str,
    csv_file_paths: List[Path]
) -> str:
    """실행을 위해 코드를 준비 (파일 경로 변수 추가 및 pd.read_csv 변환)
    
    Args:
        code: 준비할 코드
        csv_file_paths: CSV 파일 경로 목록 (Path 객체)
        
    Returns:
        실행 준비가 완료된 코드
    """
    code_to_execute = code
    
    # 1. 파일 경로 변수 생성 (도커 경로)
    filepath_vars = []
    for i, csv_file_path in enumerate(csv_file_paths):
        var_name = 'filepath' if i == 0 else f'filepath_{i+1}'
        csv_file_name = csv_file_path.name
        
        # 도커 경로 결정 (단순화: 항상 /workspace/data/ 사용)
        docker_path = f"/workspace/data/{csv_file_name}"
        filepath_vars.append(f'{var_name} = "{docker_path}"')
    
    # 2. 파일 경로 변수를 코드 맨 앞에 추가 (import 다음)
    if filepath_vars:
        import_pattern = r'(import\s+\w+[^\n]*\n)'
        if re.search(import_pattern, code_to_execute):
            # 마지막 import 문 다음에 추가
            last_import_match = list(re.finditer(import_pattern, code_to_execute))[-1]
            insert_pos = last_import_match.end()
            var_defs_code = "\n".join(filepath_vars) + "\n"
            code_to_execute = code_to_execute[:insert_pos] + var_defs_code + code_to_execute[insert_pos:]
        else:
            # import 문이 없으면 맨 앞에 추가
            var_defs_code = "\n".join(filepath_vars) + "\n\n"
            code_to_execute = var_defs_code + code_to_execute
        print(f"✅ 파일 경로 변수 추가: {', '.join([v.split('=')[0].strip() for v in filepath_vars])}")
    
    # 3. 모든 pd.read_csv 패턴을 단순하게 filepath 변수로 교체
    # 단일 파일 모드
    if len(csv_file_paths) == 1:
        # 모든 pd.read_csv("...") 패턴을 pd.read_csv(filepath)로 교체
        code_to_execute = re.sub(
            r"pd\.read_csv\(['\"][^'\"]+['\"]\)",
            'pd.read_csv(filepath)',
            code_to_execute
        )
        # pd.read_csv("...", ...) 패턴도 교체
        code_to_execute = re.sub(
            r"pd\.read_csv\(['\"][^'\"]+['\"]\s*,\s*",
            'pd.read_csv(filepath, ',
            code_to_execute
        )
        print("✅ 모든 pd.read_csv 경로를 filepath 변수로 교체 (단일 파일 모드)")
    
    # 여러 파일 모드
    else:
        # 첫 번째 파일은 filepath, 나머지는 filepath_2, filepath_3 등
        for i, csv_file_path in enumerate(csv_file_paths):
            var_name = 'filepath' if i == 0 else f'filepath_{i+1}'
            csv_file_name = csv_file_path.name
            
            # 정확한 파일명 매칭 (대소문자 무시)
            csv_file_name_lower = csv_file_name.lower()
            
            # pd.read_csv("파일명") 패턴을 해당 변수로 교체
            # 대소문자 무시 매칭
            pattern = rf"pd\.read_csv\(['\"][^'\"]*{re.escape(csv_file_name_lower.replace('.csv', ''))}[^'\"]*\.csv['\"]\)"
            code_to_execute = re.sub(
                pattern,
                f'pd.read_csv({var_name})',
                code_to_execute,
                flags=re.IGNORECASE
            )
            # pd.read_csv("파일명", ...) 패턴도 교체
            pattern_with_params = rf"pd\.read_csv\(['\"][^'\"]*{re.escape(csv_file_name_lower.replace('.csv', ''))}[^'\"]*\.csv['\"]\s*,\s*"
            code_to_execute = re.sub(
                pattern_with_params,
                f'pd.read_csv({var_name}, ',
                code_to_execute,
                flags=re.IGNORECASE
            )
        
        # 나머지 모든 pd.read_csv 패턴은 첫 번째 filepath 사용
        code_to_execute = re.sub(
            r"pd\.read_csv\(['\"][^'\"]+['\"]\)",
            'pd.read_csv(filepath)',
            code_to_execute
        )
        code_to_execute = re.sub(
            r"pd\.read_csv\(['\"][^'\"]+['\"]\s*,\s*",
            'pd.read_csv(filepath, ',
            code_to_execute
        )
        print("✅ 모든 pd.read_csv 경로를 filepath 변수로 교체 (여러 파일 모드)")
    
    # 최종 검증: filepath 변수가 사용되지만 정의되지 않은 경우 감지 및 수정
    # 1. filepath 변수 사용 패턴 확인 (pd.read_csv(filepath), filepath_2 등)
    filepath_used_patterns = [
        r'filepath\s*[,\)\]\s]',  # filepath) 또는 filepath, 또는 filepath]
        r'filepath\s*$',  # filepath로 끝나는 경우 (개행 전)
        r'filepath_\d+\s*[,\)\]\s]',  # filepath_2) 등
    ]
    
    filepath_used = False
    used_filepath_vars = set()
    
    for pattern in filepath_used_patterns:
        matches = re.finditer(pattern, code_to_execute)
        for match in matches:
            # 매칭된 부분 앞에서 변수명 추출
            before_match = code_to_execute[:match.start()]
            # filepath 또는 filepath_숫자 추출
            var_match = re.search(r'(filepath(?:_\d+)?)\s*[,\)\]\s]?$', before_match[-50:])
            if var_match:
                var_name = var_match.group(1)
                used_filepath_vars.add(var_name)
                filepath_used = True
    
    # pd.read_csv(filepath) 패턴 직접 확인
    read_csv_with_filepath = re.search(r'pd\.read_csv\s*\(\s*filepath(?:_\d+)?', code_to_execute)
    if read_csv_with_filepath:
        # 사용된 filepath 변수명 추출
        var_match = re.search(r'filepath(?:_\d+)?', read_csv_with_filepath.group(0))
        if var_match:
            used_filepath_vars.add(var_match.group(0))
            filepath_used = True
    
    # 2. filepath 변수 정의 확인
    filepath_defined = set()
    for i in range(len(csv_file_paths) + 1):  # filepath, filepath_2, ... 모두 확인
        var_name = 'filepath' if i == 0 else f'filepath_{i+1}'
        # 변수 정의 패턴: filepath = "..." 또는 filepath = ...
        if re.search(rf'{re.escape(var_name)}\s*=', code_to_execute):
            filepath_defined.add(var_name)
    
    # 3. 사용되었지만 정의되지 않은 변수 확인 및 추가
    missing_filepath_vars = used_filepath_vars - filepath_defined
    
    if missing_filepath_vars:
        print(f"⚠️ 경고: filepath 변수가 사용되지만 정의되지 않았습니다: {missing_filepath_vars}")
        
        # 누락된 변수들을 추가
        missing_vars_code = []
        for var_name in sorted(missing_filepath_vars):  # filepath 먼저, 그 다음 filepath_2, ...
            # 변수명에서 인덱스 추출
            if var_name == 'filepath':
                idx = 0
            else:
                # filepath_2 -> idx 1
                idx = int(var_name.split('_')[1]) - 1
            
            if 0 <= idx < len(csv_file_paths):
                csv_file_path = csv_file_paths[idx]
                docker_path = f"/workspace/data/{csv_file_path.name}"
                missing_vars_code.append(f'{var_name} = "{docker_path}"')
        
        if missing_vars_code:
            # import 문 다음에 추가
            import_pattern = r'(import\s+\w+[^\n]*\n)'
            if re.search(import_pattern, code_to_execute):
                last_import_match = list(re.finditer(import_pattern, code_to_execute))[-1]
                insert_pos = last_import_match.end()
                vars_code = "\n".join(missing_vars_code) + "\n"
                code_to_execute = code_to_execute[:insert_pos] + vars_code + code_to_execute[insert_pos:]
            else:
                vars_code = "\n".join(missing_vars_code) + "\n\n"
                code_to_execute = vars_code + code_to_execute
            
            print(f"✅ 누락된 filepath 변수 추가: {', '.join(missing_filepath_vars)}")
    
    # 4. pd.read_csv가 있지만 filepath 변수가 전혀 없는 경우 (하위 호환성)
    if 'pd.read_csv' in code_to_execute and not filepath_used:
        has_filepath_def = any(re.search(rf'{re.escape(var_name)}\s*=', code_to_execute) 
                               for var_name in ['filepath'] + [f'filepath_{i+1}' for i in range(len(csv_file_paths))])
        if not has_filepath_def:
            print("⚠️ 경고: pd.read_csv가 있지만 filepath 변수가 없습니다. 강제로 추가합니다.")
            # 첫 번째 파일의 도커 경로 사용
            if csv_file_paths:
                first_file = csv_file_paths[0]
                docker_path = f"/workspace/data/{first_file.name}"
                import_pattern = r'(import\s+\w+[^\n]*\n)'
                if re.search(import_pattern, code_to_execute):
                    last_import_match = list(re.finditer(import_pattern, code_to_execute))[-1]
                    insert_pos = last_import_match.end()
                    code_to_execute = code_to_execute[:insert_pos] + f'filepath = "{docker_path}"\n' + code_to_execute[insert_pos:]
                else:
                    code_to_execute = f'filepath = "{docker_path}"\n\n' + code_to_execute
                print(f"✅ filepath 변수 강제 추가: {docker_path}")
    
    return code_to_execute

