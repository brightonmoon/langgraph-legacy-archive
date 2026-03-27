"""Examples 공통 유틸리티 패키지"""
from .paths import (
    PROJECT_ROOT,
    EXAMPLES_DIR,
    TEST_DATA_DIR,
    DATA_DIR,
    get_test_csv_path,
    get_data_path,
    ensure_test_data_dir,
)
from .display import (
    print_header,
    print_section,
    print_result,
    print_separator,
    print_agent_info,
    print_test_case,
    print_success,
    print_error,
    print_warning,
    print_info,
)
from .runner import (
    run_example,
    run_async_example,
    run_test_cases,
    check_agent_ready,
)

__all__ = [
    # paths
    "PROJECT_ROOT",
    "EXAMPLES_DIR",
    "TEST_DATA_DIR",
    "DATA_DIR",
    "get_test_csv_path",
    "get_data_path",
    "ensure_test_data_dir",
    # display
    "print_header",
    "print_section",
    "print_result",
    "print_separator",
    "print_agent_info",
    "print_test_case",
    "print_success",
    "print_error",
    "print_warning",
    "print_info",
    # runner
    "run_example",
    "run_async_example",
    "run_test_cases",
    "check_agent_ready",
]
