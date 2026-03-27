#!/usr/bin/env python3
"""
문서 재분류 스크립트

completed 디렉토리의 문서들을 주제별 하위 디렉토리로 재분류합니다.
"""

import re
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

# 문서 디렉토리 경로
COMPLETED_DIR = Path(".cursor/docs/completed")

# 카테고리별 키워드 매핑
CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "architecture": [
        "architecture", "design", "pattern", "structure", "api_comparison",
        "orchestrator_worker", "workflow_architecture", "system_architecture"
    ],
    "implementation": [
        "implementation", "completion_report", "checkpointer_implementation"
    ],
    "analysis": [
        "analysis", "comparison", "gap", "vs_", "deepagent", "langchain",
        "model_creation", "llm_calls", "code_style", "current_status",
        "test_report", "feasibility"
    ],
    "integration": [
        "integration", "migration", "module_refactoring", "conversion",
        "config_dynamic", "langgraph_langchain"
    ],
    "fixes": [
        "fix", "troubleshooting", "error", "security_update", "final_status",
        "success", "refactoring_report"
    ],
    "guides": [
        "guide", "essentials", "comprehensive", "selection_guide"
    ],
    "reports": [
        "phase", "completion_report", "refactoring_report", "cleanup",
        "consolidation", "refactoring_analysis"
    ],
    "research": [
        "test_report", "research", "results", "hitl", "orchestrator_worker"
    ],
    "setup": [
        "setup", "config", "selection", "strategy", "integration_strategy",
        "cloud_integration"
    ],
    "legacy": [
        "backup", "realtime_interactive_cli"
    ]
}

# 특정 파일 매핑 (키워드로 분류되지 않는 경우)
SPECIFIC_MAPPINGS: Dict[str, str] = {
    "langgraph_api_comparison.mdc": "architecture",
    "system_architecture_summary_report.mdc": "architecture",
    "orchestrator_worker_flow_analysis.mdc": "architecture",
    "deepagent_orchestrator_worker_architecture.mdc": "architecture",
    "langgraph_report_workflow_architecture.mdc": "architecture",
    
    "coding_agent_implementation.mdc": "implementation",
    "langgraph_agent_tools_implementation_20250127.mdc": "implementation",
    "mcp_langgraph_agent_implementation.mdc": "implementation",
    "multiple_workers_coding_agent_implementation.mdc": "implementation",
    "react_agent_implementation_20250127.mdc": "implementation",
    "tool_calling_agent_implementation_20250127.mdc": "implementation",
    "langchain_agent_implementation_completion_report.mdc": "implementation",
    "checkpointer_implementation_summary.mdc": "implementation",
    
    "langchain_agents_gap_analysis.mdc": "analysis",
    "github_issues_analysis.mdc": "analysis",
    "deepagent_vs_src_comparison.mdc": "analysis",
    "langchain_sandbox_comparison.mdc": "analysis",
    "tool_calling_comparison.mdc": "analysis",
    "deep_agents_comparison_analysis.mdc": "analysis",
    "model_creation_flow_analysis.mdc": "analysis",
    "llm_calls_count_analysis.mdc": "analysis",
    "deepagent_langgraph_patterns_feasibility.mdc": "analysis",
    "langchain_code_style_analysis.mdc": "analysis",
    "langchain_agents_current_status.mdc": "analysis",
    "module_connection_test_report_20251023.mdc": "analysis",
    
    "mcp_integration_completion_report.mdc": "integration",
    "langgraph_mcp_agent_integration.mdc": "integration",
    "mcp_module_refactoring.mdc": "integration",
    "phase1_workflow_integration_report.mdc": "integration",
    "phase2_session_integration_report.mdc": "integration",
    "phase4_cli_integration_report.mdc": "integration",
    "langgraph_langchain_conversion_completion_report.mdc": "integration",
    "langchain_langgraph_refactoring.mdc": "integration",
    "mcp_config_dynamic_loading.mdc": "integration",
    
    "mcp_tool_execution_fix.mdc": "fixes",
    "langgraph_mcp_recursion_fix.mdc": "fixes",
    "filesystem_mcp_config_fix.mdc": "fixes",
    "filesystem_mcp_security_update.mdc": "fixes",
    "filesystem_mcp_final_status.mdc": "fixes",
    "filesystem_mcp_success.mdc": "fixes",
    "mcp_troubleshooting_summary.mdc": "fixes",
    "cli_error_fix_report.mdc": "fixes",
    "llm_refactoring_report.mdc": "fixes",
    
    "agent_development_essentials.mdc": "guides",
    "middleware_comprehensive_guide.mdc": "guides",
    "streaming_comprehensive_guide.mdc": "guides",
    "llm_provider_selection_guide.mdc": "guides",
    
    "phase1_completion_report.mdc": "reports",
    "phase3_data_storage_report.mdc": "reports",
    "phase5_refactoring_report.mdc": "reports",
    "langgraph_phase1_completion_report.mdc": "reports",
    "project_structure_improvement_completion_report.mdc": "reports",
    "system_cleanup_report.mdc": "reports",
    "refactoring_report_20250127.mdc": "reports",
    "refactoring_analysis.mdc": "reports",
    "readme_consolidation_20250127.mdc": "reports",
    "cli_scripts_consolidation_completion_report.mdc": "reports",
    
    "docs_langchain_mcp_test_report.mdc": "research",
    "ollama_cloud_models_test_results.mdc": "research",
    "langgraph_hitl_analysis_report.mdc": "research",
    "coding_agent_orchestrator_worker.mdc": "research",
    
    "ollama_integration_strategy.mdc": "setup",
    "ollama_cloud_cli_model_selection.mdc": "setup",
    "ollama_cloud_integration.mdc": "setup",
    
    "agentic_ai_guide_backup_20251021.mdc": "legacy",
    "realtime_interactive_cli_development.mdc": "legacy",
}


def classify_file(file_path: Path) -> str:
    """
    파일을 카테고리로 분류
    
    Returns:
        카테고리 이름 또는 "reports" (기본값)
    """
    file_name = file_path.name
    
    # 특정 매핑 확인
    if file_name in SPECIFIC_MAPPINGS:
        return SPECIFIC_MAPPINGS[file_name]
    
    # 키워드 기반 분류
    file_name_lower = file_name.lower()
    
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in file_name_lower:
                return category
    
    # 기본값: reports
    return "reports"


def main():
    """메인 함수"""
    print("=" * 60)
    print("문서 재분류 스크립트")
    print("=" * 60)
    print(f"대상 디렉토리: {COMPLETED_DIR.absolute()}")
    print()
    
    # 모든 .mdc 파일 찾기 (하위 디렉토리 제외)
    mdc_files = [f for f in COMPLETED_DIR.glob("*.mdc") if f.is_file()]
    
    if not mdc_files:
        print("❌ .mdc 파일을 찾을 수 없습니다.")
        return
    
    print(f"발견된 파일 수: {len(mdc_files)}")
    print()
    
    # 분류 통계
    classification_stats: Dict[str, List[Path]] = {}
    
    # 각 파일 분류
    for file_path in sorted(mdc_files):
        category = classify_file(file_path)
        
        if category not in classification_stats:
            classification_stats[category] = []
        classification_stats[category].append(file_path)
    
    # 분류 결과 출력
    print("분류 결과:")
    print("-" * 60)
    for category, files in sorted(classification_stats.items()):
        print(f"{category:20s}: {len(files):3d}개")
    print()
    
    # 사용자 확인
    print("다음 작업을 수행합니다:")
    print("1. 각 파일을 해당 카테고리 디렉토리로 이동")
    print("2. classification_design.mdc는 그대로 유지")
    print()
    
    # 파일 이동
    moved_count = 0
    for category, files in classification_stats.items():
        category_dir = COMPLETED_DIR / category
        category_dir.mkdir(exist_ok=True)
        
        for file_path in files:
            # classification_design.mdc는 이동하지 않음
            if file_path.name == "classification_design.mdc":
                continue
            
            dest_path = category_dir / file_path.name
            
            try:
                shutil.move(str(file_path), str(dest_path))
                moved_count += 1
            except Exception as e:
                print(f"❌ 이동 실패: {file_path.name} - {e}")
    
    print()
    print("=" * 60)
    print("재분류 완료 요약")
    print("=" * 60)
    print(f"처리된 파일 수: {len(mdc_files)}")
    print(f"이동된 파일 수: {moved_count}")
    print()
    
    print("카테고리별 파일 수:")
    for category, files in sorted(classification_stats.items()):
        print(f"  {category:20s}: {len(files):3d}개")
    
    print()
    print("✅ 문서 재분류 완료!")


if __name__ == "__main__":
    main()




