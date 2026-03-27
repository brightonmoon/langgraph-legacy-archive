"""
MinerU vlm-lmdeploy-engine 리소스 사용량 비교 테스트 스크립트

두 PDF 파일의 크기에 따른 처리 리소스량 및 시간을 비교합니다.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import List, Optional

try:
    import psutil
except ImportError:
    psutil = None

GPU_AVAILABLE = False
try:
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=index", "--format=csv,noheader"],
        capture_output=True,
        text=True,
        timeout=2,
    )
    if result.returncode == 0 and result.stdout.strip():
        GPU_AVAILABLE = True
except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
    GPU_AVAILABLE = False


@dataclass
class ResourceSnapshot:
    """리소스 사용량 스냅샷"""
    cpu_percent: float
    memory_mb: float
    gpu_percent: Optional[float] = None
    gpu_memory_mb: Optional[float] = None
    gpu_total_memory_mb: Optional[float] = None
    timestamp: Optional[str] = None


@dataclass
class TestResult:
    """테스트 결과"""
    pdf_name: str
    pdf_size_mb: float
    page_count: int = 0
    processing_time_seconds: float = 0.0
    success: bool = False
    output_dir: Optional[str] = None
    error_message: Optional[str] = None
    
    # 리소스 사용량 (최대값)
    max_cpu_percent: float = 0.0
    max_memory_mb: float = 0.0
    max_gpu_percent: Optional[float] = None
    max_gpu_memory_mb: Optional[float] = None
    
    # 리소스 사용량 (평균값)
    avg_cpu_percent: float = 0.0
    avg_memory_mb: float = 0.0
    avg_gpu_percent: Optional[float] = None
    avg_gpu_memory_mb: Optional[float] = None
    
    # 리소스 스냅샷 리스트
    resource_snapshots: List[ResourceSnapshot] = None
    
    def __post_init__(self):
        if self.resource_snapshots is None:
            self.resource_snapshots = []
    
    @property
    def time_per_page(self) -> float:
        """페이지당 처리 시간 (초)"""
        return self.processing_time_seconds / self.page_count if self.page_count > 0 else 0.0
    
    @property
    def memory_per_page(self) -> float:
        """페이지당 메모리 사용량 (MB)"""
        return self.max_memory_mb / self.page_count if self.page_count > 0 else 0.0
    
    @property
    def gpu_memory_per_page(self) -> Optional[float]:
        """페이지당 GPU 메모리 사용량 (MB)"""
        if self.max_gpu_memory_mb is None or self.page_count == 0:
            return None
        return self.max_gpu_memory_mb / self.page_count


class ResourceMonitor:
    """리소스 모니터링 클래스"""
    
    def __init__(self, interval: float = 0.5):
        self.interval = interval
        self.snapshots: List[ResourceSnapshot] = []
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
    
    def _get_resource_snapshot(self) -> ResourceSnapshot:
        """현재 리소스 사용량 스냅샷 생성"""
        cpu_percent = 0.0
        memory_mb = 0.0
        gpu_percent = None
        gpu_memory_mb = None
        gpu_total_memory_mb = None
        
        # CPU and Memory
        if psutil:
            # 시스템 전체 CPU 사용률
            cpu_percent = psutil.cpu_percent(interval=0.1)
            # 시스템 전체 메모리 사용률
            memory = psutil.virtual_memory()
            memory_mb = memory.used / 1024 / 1024
        
        # GPU (using nvidia-smi)
        if GPU_AVAILABLE:
            try:
                result = subprocess.run(
                    [
                        "nvidia-smi",
                        "--query-gpu=utilization.gpu,memory.used,memory.total",
                        "--format=csv,noheader,nounits",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                if result.returncode == 0:
                    parts = result.stdout.strip().split(", ")
                    if len(parts) >= 3:
                        gpu_percent = float(parts[0])
                        gpu_memory_mb = float(parts[1])
                        gpu_total_memory_mb = float(parts[2])
            except (subprocess.TimeoutExpired, ValueError, Exception):
                pass
        
        return ResourceSnapshot(
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            gpu_percent=gpu_percent,
            gpu_memory_mb=gpu_memory_mb,
            gpu_total_memory_mb=gpu_total_memory_mb,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    
    def _monitor_loop(self):
        """모니터링 루프"""
        while self.monitoring:
            snapshot = self._get_resource_snapshot()
            self.snapshots.append(snapshot)
            time.sleep(self.interval)
    
    def start(self):
        """모니터링 시작"""
        self.snapshots = []
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop(self) -> List[ResourceSnapshot]:
        """모니터링 중지 및 스냅샷 반환"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        return self.snapshots.copy()
    
    def get_statistics(self, snapshots: List[ResourceSnapshot]) -> dict:
        """스냅샷 리스트에서 통계 계산"""
        if not snapshots:
            return {
                "max_cpu_percent": 0.0,
                "max_memory_mb": 0.0,
                "max_gpu_percent": None,
                "max_gpu_memory_mb": None,
                "avg_cpu_percent": 0.0,
                "avg_memory_mb": 0.0,
                "avg_gpu_percent": None,
                "avg_gpu_memory_mb": None,
            }
        
        cpu_values = [s.cpu_percent for s in snapshots]
        memory_values = [s.memory_mb for s in snapshots]
        gpu_percent_values = [s.gpu_percent for s in snapshots if s.gpu_percent is not None]
        gpu_memory_values = [s.gpu_memory_mb for s in snapshots if s.gpu_memory_mb is not None]
        
        stats = {
            "max_cpu_percent": max(cpu_values) if cpu_values else 0.0,
            "max_memory_mb": max(memory_values) if memory_values else 0.0,
            "avg_cpu_percent": sum(cpu_values) / len(cpu_values) if cpu_values else 0.0,
            "avg_memory_mb": sum(memory_values) / len(memory_values) if memory_values else 0.0,
        }
        
        if gpu_percent_values:
            stats["max_gpu_percent"] = max(gpu_percent_values)
            stats["avg_gpu_percent"] = sum(gpu_percent_values) / len(gpu_percent_values)
        else:
            stats["max_gpu_percent"] = None
            stats["avg_gpu_percent"] = None
        
        if gpu_memory_values:
            stats["max_gpu_memory_mb"] = max(gpu_memory_values)
            stats["avg_gpu_memory_mb"] = sum(gpu_memory_values) / len(gpu_memory_values)
        else:
            stats["max_gpu_memory_mb"] = None
            stats["avg_gpu_memory_mb"] = None
        
        return stats


def get_pdf_size_mb(pdf_path: Path) -> float:
    """PDF 파일 크기를 MB 단위로 반환"""
    if not pdf_path.exists():
        return 0.0
    return pdf_path.stat().st_size / (1024 * 1024)


def get_pdf_page_count(pdf_path: Path) -> int:
    """PDF 파일의 페이지 수를 반환"""
    if not pdf_path.exists():
        return 0
    
    # pypdf를 사용하여 페이지 수 가져오기
    try:
        import pypdf
        with open(pdf_path, 'rb') as f:
            pdf_reader = pypdf.PdfReader(f)
            return len(pdf_reader.pages)
    except ImportError:
        # pypdf가 없으면 PyMuPDF 시도
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(str(pdf_path))
            page_count = len(doc)
            doc.close()
            return page_count
        except ImportError:
            # 둘 다 없으면 0 반환
            return 0
    except Exception:
        return 0


def run_mineru(
    pdf_path: Path,
    output_base_dir: Path,
    device: str = "cuda:0",
) -> tuple[bool, Optional[str], Optional[str], float]:
    """
    MinerU를 실행하여 PDF를 변환
    
    Returns:
        (success, output_dir, error_message, processing_time)
    """
    # 출력 디렉토리 생성
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_dir = output_base_dir / f"mineru_{pdf_path.stem}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # MinerU 명령어 구성
    cmd = [
        "mineru",
        "-p", str(pdf_path),
        "-o", str(output_dir),
        "-b", "vlm-lmdeploy-engine",
        "-d", device,
    ]
    
    print(f"  📄 처리 중: {pdf_path.name}")
    print(f"  📁 출력 디렉토리: {output_dir}")
    print(f"  ⚙️  디바이스: {device}")
    
    # 실행 시간 측정
    start_time = perf_counter()
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=3600,  # 1시간 타임아웃
        )
        
        processing_time = perf_counter() - start_time
        
        if result.returncode == 0:
            # 출력 파일 확인
            md_files = list(output_dir.rglob("*.md"))
            if md_files:
                return True, str(output_dir), None, processing_time
            else:
                return False, str(output_dir), "출력 파일이 생성되지 않았습니다", processing_time
        else:
            return False, str(output_dir), result.stderr, processing_time
    
    except subprocess.TimeoutExpired:
        processing_time = perf_counter() - start_time
        return False, str(output_dir), "타임아웃 (1시간 초과)", processing_time
    except Exception as e:
        processing_time = perf_counter() - start_time
        return False, str(output_dir), str(e), processing_time


def test_pdf(
    pdf_path: Path,
    output_base_dir: Path,
    device: str = "cuda:0",
) -> TestResult:
    """단일 PDF 파일에 대한 테스트 실행"""
    pdf_name = pdf_path.name
    pdf_size_mb = get_pdf_size_mb(pdf_path)
    page_count = get_pdf_page_count(pdf_path)
    
    print(f"\n{'='*60}")
    print(f"테스트 시작: {pdf_name}")
    print(f"파일 크기: {pdf_size_mb:.2f} MB")
    print(f"페이지 수: {page_count} 페이지")
    print(f"{'='*60}")
    
    # 리소스 모니터 시작
    monitor = ResourceMonitor(interval=0.5)
    monitor.start()
    
    # MinerU 실행
    success, output_dir, error_message, processing_time = run_mineru(
        pdf_path, output_base_dir, device
    )
    
    # 리소스 모니터 중지
    snapshots = monitor.stop()
    stats = monitor.get_statistics(snapshots)
    
    # 결과 생성
    result = TestResult(
        pdf_name=pdf_name,
        pdf_size_mb=pdf_size_mb,
        page_count=page_count,
        processing_time_seconds=processing_time,
        success=success,
        output_dir=output_dir,
        error_message=error_message,
        max_cpu_percent=stats["max_cpu_percent"],
        max_memory_mb=stats["max_memory_mb"],
        max_gpu_percent=stats["max_gpu_percent"],
        max_gpu_memory_mb=stats["max_gpu_memory_mb"],
        avg_cpu_percent=stats["avg_cpu_percent"],
        avg_memory_mb=stats["avg_memory_mb"],
        avg_gpu_percent=stats["avg_gpu_percent"],
        avg_gpu_memory_mb=stats["avg_gpu_memory_mb"],
        resource_snapshots=snapshots,
    )
    
    # 결과 출력
    print(f"\n✅ 테스트 완료")
    print(f"  처리 시간: {processing_time:.2f}초")
    if page_count > 0:
        print(f"  페이지당 처리 시간: {result.time_per_page:.2f}초/페이지")
    print(f"  성공 여부: {'✅ 성공' if success else '❌ 실패'}")
    if error_message:
        print(f"  오류: {error_message}")
    print(f"  최대 CPU: {stats['max_cpu_percent']:.1f}%")
    print(f"  최대 메모리: {stats['max_memory_mb']:.1f} MB")
    if page_count > 0:
        print(f"  페이지당 메모리: {result.memory_per_page:.1f} MB/페이지")
    if stats['max_gpu_percent'] is not None:
        print(f"  최대 GPU: {stats['max_gpu_percent']:.1f}%")
    if stats['max_gpu_memory_mb'] is not None:
        print(f"  최대 GPU 메모리: {stats['max_gpu_memory_mb']:.1f} MB")
        if page_count > 0 and result.gpu_memory_per_page:
            print(f"  페이지당 GPU 메모리: {result.gpu_memory_per_page:.1f} MB/페이지")
    
    return result


def generate_comparison_report(
    results: List[TestResult],
    output_dir: Path,
) -> Path:
    """비교 보고서 생성"""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_path = output_dir / f"mineru_resource_comparison_{timestamp}.md"
    
    # 결과 정렬 (페이지 수 순)
    sorted_results = sorted(results, key=lambda r: r.page_count)
    
    # 보고서 내용 생성
    report_lines = [
        "# MinerU vlm-lmdeploy-engine 리소스 사용량 비교 보고서",
        "",
        f"**생성 시간**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}",
        f"**백엔드**: vlm-lmdeploy-engine",
        f"**테스트 파일 수**: {len(results)}",
        "",
        "---",
        "",
        "## 📊 결과 요약",
        "",
        "| 파일명 | 파일 크기 (MB) | 페이지 수 | 처리 시간 (초) | 페이지당 시간 (초) | 최대 CPU (%) | 최대 메모리 (MB) | 페이지당 메모리 (MB) | 최대 GPU (%) | 최대 GPU 메모리 (MB) | 성공 여부 |",
        "|--------|--------------|----------|---------------|------------------|-------------|----------------|-------------------|-------------|-------------------|----------|",
    ]
    
    for result in sorted_results:
        gpu_str = f"{result.max_gpu_percent:.1f}" if result.max_gpu_percent is not None else "N/A"
        gpu_mem_str = f"{result.max_gpu_memory_mb:.1f}" if result.max_gpu_memory_mb is not None else "N/A"
        success_str = "✅" if result.success else "❌"
        time_per_page = result.time_per_page if result.page_count > 0 else 0.0
        mem_per_page = result.memory_per_page if result.page_count > 0 else 0.0
        
        report_lines.append(
            f"| {result.pdf_name} | {result.pdf_size_mb:.2f} | {result.page_count} | "
            f"{result.processing_time_seconds:.2f} | {time_per_page:.2f} | "
            f"{result.max_cpu_percent:.1f} | {result.max_memory_mb:.1f} | {mem_per_page:.1f} | "
            f"{gpu_str} | {gpu_mem_str} | {success_str} |"
        )
    
    report_lines.extend([
        "",
        "## 📈 상세 비교",
        "",
    ])
    
    # 각 파일별 상세 정보
    for i, result in enumerate(sorted_results, 1):
        report_lines.extend([
            f"### {i}. {result.pdf_name}",
            "",
            "#### 파일 정보",
            f"- **파일 크기**: {result.pdf_size_mb:.2f} MB",
            f"- **페이지 수**: {result.page_count} 페이지",
            f"- **처리 시간**: {result.processing_time_seconds:.2f}초",
            f"- **페이지당 처리 시간**: {result.time_per_page:.2f}초/페이지" if result.page_count > 0 else "",
            f"- **성공 여부**: {'✅ 성공' if result.success else '❌ 실패'}",
            "",
            "#### 리소스 사용량 (최대값)",
            f"- **CPU 사용률**: {result.max_cpu_percent:.1f}%",
            f"- **메모리 사용량**: {result.max_memory_mb:.1f} MB",
            f"- **페이지당 메모리**: {result.memory_per_page:.1f} MB/페이지" if result.page_count > 0 else "",
        ])
        
        if result.max_gpu_percent is not None:
            report_lines.append(f"- **GPU 사용률**: {result.max_gpu_percent:.1f}%")
        if result.max_gpu_memory_mb is not None:
            gpu_mem_line = f"- **GPU 메모리**: {result.max_gpu_memory_mb:.1f} MB"
            if result.gpu_memory_per_page is not None:
                gpu_mem_line += f" ({result.gpu_memory_per_page:.1f} MB/페이지)"
            report_lines.append(gpu_mem_line)
        
        report_lines.extend([
            "",
            "#### 리소스 사용량 (평균값)",
            f"- **CPU 사용률**: {result.avg_cpu_percent:.1f}%",
            f"- **메모리 사용량**: {result.avg_memory_mb:.1f} MB",
        ])
        
        if result.avg_gpu_percent is not None:
            report_lines.append(f"- **GPU 사용률**: {result.avg_gpu_percent:.1f}%")
        if result.avg_gpu_memory_mb is not None:
            report_lines.append(f"- **GPU 메모리**: {result.avg_gpu_memory_mb:.1f} MB")
        
        if result.output_dir:
            report_lines.append(f"- **출력 디렉토리**: {result.output_dir}")
        
        if result.error_message:
            report_lines.extend([
                "",
                "#### 오류 정보",
                f"```",
                f"{result.error_message}",
                f"```",
            ])
        
        report_lines.append("")
    
    # 비교 분석
    if len(sorted_results) == 2:
        small = sorted_results[0]  # 페이지 수가 적은 파일
        large = sorted_results[1]  # 페이지 수가 많은 파일
        
        report_lines.extend([
            "## 🔍 비교 분석",
            "",
            "### 파일 정보 비교",
            f"- **파일 크기**:",
            f"  - {small.pdf_name}: {small.pdf_size_mb:.2f} MB",
            f"  - {large.pdf_name}: {large.pdf_size_mb:.2f} MB",
            f"  - 크기 비율: {large.pdf_size_mb / small.pdf_size_mb:.2f}배",
            "",
            f"- **페이지 수**:",
            f"  - {small.pdf_name}: {small.page_count} 페이지",
            f"  - {large.pdf_name}: {large.page_count} 페이지",
            f"  - 페이지 비율: {large.page_count / small.page_count:.2f}배",
            "",
            f"- **페이지당 파일 크기**:",
            f"  - {small.pdf_name}: {small.pdf_size_mb / small.page_count:.2f} MB/페이지" if small.page_count > 0 else "",
            f"  - {large.pdf_name}: {large.pdf_size_mb / large.page_count:.2f} MB/페이지" if large.page_count > 0 else "",
            "",
            "### 처리 시간 비교",
            f"- **전체 처리 시간**:",
            f"  - {small.pdf_name}: {small.processing_time_seconds:.2f}초",
            f"  - {large.pdf_name}: {large.processing_time_seconds:.2f}초",
            f"  - 시간 비율: {large.processing_time_seconds / small.processing_time_seconds:.2f}배",
            "",
            f"- **페이지당 처리 시간** (효율성 지표):",
            f"  - {small.pdf_name}: {small.time_per_page:.2f}초/페이지",
            f"  - {large.pdf_name}: {large.time_per_page:.2f}초/페이지",
            f"  - 효율성 비율: {large.time_per_page / small.time_per_page:.2f}배" if small.time_per_page > 0 else "",
            "",
            "### 리소스 사용량 비교",
            "",
            "#### CPU 사용률",
            f"- {small.pdf_name} (최대): {small.max_cpu_percent:.1f}%",
            f"- {large.pdf_name} (최대): {large.max_cpu_percent:.1f}%",
            f"- 차이: {abs(large.max_cpu_percent - small.max_cpu_percent):.1f}%p",
            "",
            "#### 메모리 사용량",
            f"- {small.pdf_name} (최대): {small.max_memory_mb:.1f} MB",
            f"- {large.pdf_name} (최대): {large.max_memory_mb:.1f} MB",
            f"- 차이: {abs(large.max_memory_mb - small.max_memory_mb):.1f} MB",
            "",
            f"- **페이지당 메모리 사용량**:",
            f"  - {small.pdf_name}: {small.memory_per_page:.1f} MB/페이지",
            f"  - {large.pdf_name}: {large.memory_per_page:.1f} MB/페이지",
            f"  - 효율성 비율: {large.memory_per_page / small.memory_per_page:.2f}배" if small.memory_per_page > 0 else "",
        ])
        
        if small.max_gpu_percent is not None and large.max_gpu_percent is not None:
            report_lines.extend([
                "",
                "#### GPU 사용률",
                f"- {small.pdf_name} (최대): {small.max_gpu_percent:.1f}%",
                f"- {large.pdf_name} (최대): {large.max_gpu_percent:.1f}%",
                f"- 차이: {abs(large.max_gpu_percent - small.max_gpu_percent):.1f}%p",
            ])
        
        if small.max_gpu_memory_mb is not None and large.max_gpu_memory_mb is not None:
            report_lines.extend([
                "",
                "#### GPU 메모리 사용량",
                f"- {small.pdf_name} (최대): {small.max_gpu_memory_mb:.1f} MB",
                f"- {large.pdf_name} (최대): {large.max_gpu_memory_mb:.1f} MB",
                f"- 차이: {abs(large.max_gpu_memory_mb - small.max_gpu_memory_mb):.1f} MB",
            ])
            if small.gpu_memory_per_page is not None and large.gpu_memory_per_page is not None:
                report_lines.extend([
                    "",
                    f"- **페이지당 GPU 메모리 사용량**:",
                    f"  - {small.pdf_name}: {small.gpu_memory_per_page:.1f} MB/페이지",
                    f"  - {large.pdf_name}: {large.gpu_memory_per_page:.1f} MB/페이지",
                    f"  - 효율성 비율: {large.gpu_memory_per_page / small.gpu_memory_per_page:.2f}배" if small.gpu_memory_per_page > 0 else "",
                ])
        
        # 주요 인사이트
        report_lines.extend([
            "",
            "### 💡 주요 인사이트",
            "",
        ])
        
        if small.time_per_page > 0 and large.time_per_page > 0:
            if large.time_per_page < small.time_per_page:
                report_lines.append(
                    f"- **처리 효율성**: {large.pdf_name}이 페이지당 {small.time_per_page / large.time_per_page:.2f}배 더 빠르게 처리됩니다. "
                    f"이는 페이지 수가 많을수록 배치 처리 효율이 향상됨을 의미합니다."
                )
            else:
                report_lines.append(
                    f"- **처리 효율성**: {small.pdf_name}이 페이지당 {large.time_per_page / small.time_per_page:.2f}배 더 빠르게 처리됩니다. "
                    f"이는 파일의 복잡도나 레이아웃이 처리 시간에 큰 영향을 미침을 의미합니다."
                )
        
        if small.memory_per_page > 0 and large.memory_per_page > 0:
            if large.memory_per_page < small.memory_per_page:
                report_lines.append(
                    f"- **메모리 효율성**: {large.pdf_name}이 페이지당 {small.memory_per_page / large.memory_per_page:.2f}배 더 적은 메모리를 사용합니다."
                )
            else:
                report_lines.append(
                    f"- **메모리 효율성**: {small.pdf_name}이 페이지당 {large.memory_per_page / small.memory_per_page:.2f}배 더 적은 메모리를 사용합니다."
                )
        
        report_lines.append("")
    
    report_lines.extend([
        "## 📝 참고사항",
        "",
        "- 이 보고서는 MinerU vlm-lmdeploy-engine 백엔드를 사용하여 생성되었습니다.",
        "- 리소스 사용량은 시스템 전체 사용량을 모니터링한 결과입니다.",
        "- 결과는 시스템 환경과 하드웨어 사양에 따라 달라질 수 있습니다.",
        "- GPU 사용량은 nvidia-smi를 통해 측정되었습니다.",
        "",
    ])
    
    # JSON 데이터도 저장
    json_path = output_dir / f"mineru_resource_comparison_{timestamp}.json"
    json_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "backend": "vlm-lmdeploy-engine",
        "results": [asdict(result) for result in sorted_results],
    }
    
    # resource_snapshots는 너무 크므로 제외
    for result_dict in json_data["results"]:
        if "resource_snapshots" in result_dict:
            result_dict["resource_snapshots"] = f"({len(result_dict['resource_snapshots'])} snapshots)"
    
    json_path.write_text(json.dumps(json_data, indent=2, ensure_ascii=False), encoding="utf-8")
    
    # 보고서 저장
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    
    return report_path


def main():
    """메인 함수"""
    # 경로 설정
    comparison_dir = Path("/home/doyamoon/agentic_ai/comparison")
    output_base_dir = Path("/home/doyamoon/agentic_ai/tests/test_output/mineru_comparison")
    output_base_dir.mkdir(parents=True, exist_ok=True)
    
    # 테스트할 PDF 파일 목록 (모든 comparison 디렉토리의 PDF 파일)
    pdf_files = sorted(comparison_dir.glob("*.pdf"))
    
    # 존재하는 파일만 필터링
    pdf_files = [f for f in pdf_files if f.exists()]
    
    if not pdf_files:
        print("❌ 테스트할 PDF 파일을 찾을 수 없습니다.")
        return
    
    print(f"\n{'='*60}")
    print(f"MinerU vlm-lmdeploy-engine 리소스 비교 테스트")
    print(f"{'='*60}")
    print(f"테스트 파일 수: {len(pdf_files)}")
    print(f"출력 디렉토리: {output_base_dir}")
    print(f"GPU 사용 가능: {'✅' if GPU_AVAILABLE else '❌'}")
    print(f"{'='*60}\n")
    
    # 각 파일에 대해 테스트 실행
    results = []
    device = "cuda:0" if GPU_AVAILABLE else "cpu"
    
    for pdf_path in pdf_files:
        result = test_pdf(pdf_path, output_base_dir, device)
        results.append(result)
        
        # 파일 간 간격 (세션 정리 시간)
        if pdf_path != pdf_files[-1]:
            print("\n⏳ 다음 파일 처리 전 대기 중... (3초)")
            time.sleep(3)
    
    # 비교 보고서 생성
    print(f"\n{'='*60}")
    print(f"비교 보고서 생성 중...")
    print(f"{'='*60}")
    
    report_path = generate_comparison_report(results, output_base_dir)
    
    print(f"\n✅ 테스트 완료!")
    print(f"📄 보고서: {report_path}")
    print(f"\n📊 요약:")
    for result in results:
        status = "✅" if result.success else "❌"
        print(f"  {status} {result.pdf_name}: {result.processing_time_seconds:.2f}초")


if __name__ == "__main__":
    main()

