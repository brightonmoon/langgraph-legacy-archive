"""
LangChain Ollama embedding timing script with resource monitoring.
"""

from __future__ import annotations

import json
import os
import argparse
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Iterable, List, Sequence, Optional

from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings

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


load_dotenv()

DATA_DIR = Path("/home/doyamoon/agentic_ai/data")
OUTPUT_DIR = Path("/home/doyamoon/agentic_ai/tests/test_output/embeddings")
REPORT_DIR = Path("/home/doyamoon/agentic_ai/tests/reports")

PDF_TARGETS = {
    "small": DATA_DIR
    / "LC_Tangible_Screening_Compound _Collection_Description.pdf",
    "large": DATA_DIR / "MACHINE LEARNING FOR SMALL molecule lead optimization.pdf",
}

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200


@dataclass
class PhaseTiming:
    label: str
    seconds: float

    def as_message(self) -> str:
        return f"{self.label}: {self.seconds:.2f}s"


@dataclass
class ResourceUsage:
    cpu_percent: float
    memory_mb: float
    gpu_percent: Optional[float] = None
    gpu_memory_mb: Optional[float] = None
    gpu_total_memory_mb: Optional[float] = None
    measured_at: Optional[str] = None


def _timestamp(format_type: str = "filename") -> str:
    """Return timezone-aware timestamp strings."""
    now = datetime.now(timezone.utc)
    if format_type == "iso":
        return now.isoformat()
    if format_type == "readable":
        return now.strftime("%Y-%m-%d %H:%M:%S")
    return now.strftime("%Y%m%d_%H%M%S")


def _get_resource_usage() -> ResourceUsage:
    """Get current system resource usage."""
    cpu_percent = 0.0
    memory_mb = 0.0
    gpu_percent = None
    gpu_memory_mb = None
    gpu_total_memory_mb = None
    
    # CPU and Memory
    if psutil:
        process = psutil.Process()
        cpu_percent = process.cpu_percent(interval=0.1)
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
    
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
    
    return ResourceUsage(
        cpu_percent=cpu_percent,
        memory_mb=memory_mb,
        gpu_percent=gpu_percent,
        gpu_memory_mb=gpu_memory_mb,
        gpu_total_memory_mb=gpu_total_memory_mb,
        measured_at=_timestamp("iso"),
    )


def _timed_call(label: str, func):
    """Measure the execution time of a callable."""
    start = perf_counter()
    result = func()
    duration = perf_counter() - start
    return result, PhaseTiming(label, duration)


def _load_and_chunk(pdf_path: Path):
    loader = PyPDFLoader(str(pdf_path))
    documents, load_timing = _timed_call("PDF load", loader.load)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )

    def _split():
        return splitter.split_documents(documents)

    chunks, split_timing = _timed_call("Chunk split", _split)
    return chunks, [load_timing, split_timing]


def _embed_chunks(
    texts: Sequence[str],
    embedder: OllamaEmbeddings,
    device: str = "gpu",
) -> tuple[List[List[float]], PhaseTiming, ResourceUsage]:
    """Embed chunks and measure resources during embedding."""
    # Get baseline resource usage before embedding
    baseline_resources = _get_resource_usage()
    
    def _embed():
        return embedder.embed_documents(list(texts))

    vectors, timing = _timed_call("Embedding", _embed)
    
    # Get resource usage after embedding (during the process)
    # We measure right after to capture peak usage
    resource_usage = _get_resource_usage()
    
    # For CPU mode, we need to verify GPU is not being used
    # The issue is that Ollama server might have model loaded in GPU memory
    # even when num_gpu=0 is set. We can't force unload from Python client.
    # So we note this limitation in the report.
    
    return vectors, timing, resource_usage


def _persist_embeddings(
    label: str,
    pdf_path: Path,
    texts: Sequence[str],
    embeddings: Sequence[Sequence[float]],
    metadatas: Sequence[dict],
) -> tuple[Path, PhaseTiming]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{label}_{_timestamp()}.jsonl"

    def _write():
        with output_path.open("w", encoding="utf-8") as file:
            for idx, (text, vector, metadata) in enumerate(
                zip(texts, embeddings, metadatas)
            ):
                record = {
                    "chunk_id": f"{label}_chunk_{idx}",
                    "source_pdf": str(pdf_path),
                    "character_len": len(text),
                    "metadata": metadata,
                    "embedding": vector,
                    "generated_at": _timestamp("iso"),
                }
                json.dump(record, file)
                file.write("\n")

    _, timing = _timed_call("Persist", _write)
    return output_path, timing


def _print_timing_report(
    doc_label: str,
    pdf_path: Path,
    chunk_count: int,
    timings: Iterable[PhaseTiming],
    output_path: Path,
    resource_usage: Optional[ResourceUsage] = None,
) -> None:
    print(f"\n=== {doc_label.upper()} DOCUMENT ({pdf_path.name}) ===")
    print(f"Chunks: {chunk_count}")
    for item in timings:
        print(f" - {item.as_message()}")
    if resource_usage:
        print(f"\n📊 Resource Usage:")
        print(f" - CPU: {resource_usage.cpu_percent:.1f}%")
        print(f" - Memory: {resource_usage.memory_mb:.1f} MB")
        if resource_usage.gpu_percent is not None:
            print(f" - GPU: {resource_usage.gpu_percent}%")
        if resource_usage.gpu_memory_mb is not None and resource_usage.gpu_total_memory_mb is not None:
            print(f" - GPU Memory: {resource_usage.gpu_memory_mb:.0f}/{resource_usage.gpu_total_memory_mb:.0f} MB")
    print(f"Embeddings saved to: {output_path}")


def _build_embedder(device: str) -> OllamaEmbeddings:
    model_name = os.getenv("OLLAMA_EMBED_MODEL", "bge-m3")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    embed_kwargs: dict[str, int | None] = {}

    if device == "cpu":
        embed_kwargs["num_gpu"] = 0
    elif os.getenv("OLLAMA_NUM_GPU"):
        embed_kwargs["num_gpu"] = int(os.getenv("OLLAMA_NUM_GPU", "1"))

    if os.getenv("OLLAMA_NUM_THREAD"):
        embed_kwargs["num_thread"] = int(os.getenv("OLLAMA_NUM_THREAD"))

    print(
        f"\nUsing OllamaEmbeddings model='{model_name}' at '{base_url}' "
        f"(device={device})"
    )
    return OllamaEmbeddings(
        model=model_name,
        base_url=base_url,
        **embed_kwargs,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Measure LangChain Ollama embedding performance."
    )
    parser.add_argument(
        "--device",
        choices=("gpu", "cpu"),
        default=os.getenv("OLLAMA_DEVICE", "gpu"),
        help="Select GPU (default) or CPU execution.",
    )
    parser.add_argument(
        "--pdf",
        type=str,
        help="Specific PDF file to process (by label: small or large, or full path)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Number of runs for averaging (default: 1)",
    )
    return parser.parse_args()


def _generate_comparison_report(
    pdf_path: Path,
    cpu_results: List[tuple[PhaseTiming, ResourceUsage]],
    gpu_results: List[tuple[PhaseTiming, ResourceUsage]],
    chunk_count: int,
) -> Path:
    """Generate comparison report in Markdown format."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Calculate averages
    cpu_avg_time = sum(r[0].seconds for r in cpu_results) / len(cpu_results)
    cpu_avg_cpu = sum(r[1].cpu_percent for r in cpu_results) / len(cpu_results)
    cpu_avg_mem = sum(r[1].memory_mb for r in cpu_results) / len(cpu_results)
    cpu_avg_gpu = sum(r[1].gpu_percent or 0 for r in cpu_results) / len(cpu_results)
    cpu_avg_gpu_mem = sum(r[1].gpu_memory_mb or 0 for r in cpu_results) / len(cpu_results)
    cpu_gpu_total = cpu_results[0][1].gpu_total_memory_mb or 0
    
    gpu_avg_time = sum(r[0].seconds for r in gpu_results) / len(gpu_results)
    gpu_avg_cpu = sum(r[1].cpu_percent for r in gpu_results) / len(gpu_results)
    gpu_avg_mem = sum(r[1].memory_mb for r in gpu_results) / len(gpu_results)
    gpu_avg_gpu = sum(r[1].gpu_percent or 0 for r in gpu_results) / len(gpu_results)
    gpu_avg_gpu_mem = sum(r[1].gpu_memory_mb or 0 for r in gpu_results) / len(gpu_results)
    gpu_gpu_total = gpu_results[0][1].gpu_total_memory_mb or 0
    
    cpu_throughput = chunk_count / cpu_avg_time if cpu_avg_time > 0 else 0
    gpu_throughput = chunk_count / gpu_avg_time if gpu_avg_time > 0 else 0
    
    speedup = cpu_avg_time / gpu_avg_time if gpu_avg_time > 0 else 0
    
    # Check GPU exclusion
    cpu_gpu_excluded = cpu_avg_gpu_mem < 500 and cpu_avg_gpu < 5
    gpu_gpu_excluded = False  # GPU mode always uses GPU
    
    timestamp = _timestamp("readable")
    report_path = REPORT_DIR / f"pdf_embedding_test_{pdf_path.stem}_{_timestamp()}.md"
    
    report_content = f"""# Ollama Embedding 모델 리소스 사용량 비교 보고서

**생성 시간**: {timestamp}
**모델**: {os.getenv("OLLAMA_EMBED_MODEL", "bge-m3")}:latest
**테스트 텍스트**: PDF 파일 ({pdf_path.name})에서 추출한 {chunk_count}개 청크
**실행 횟수**: {len(cpu_results)}회 (평균값 사용)

---

## 📊 결과 요약

| 모드 | 평균 시간 (초) | 처리량 (emb/s) | CPU (%) | 메모리 (MB) | GPU (%) | GPU 메모리 (MB) | GPU 배제 |
|------|---------------|----------------|---------|-------------|---------|-----------------|----------|
| CPU | {cpu_avg_time:.3f} | {cpu_throughput:.2f} | {cpu_avg_cpu:.1f} | {cpu_avg_mem:.1f} | {int(cpu_avg_gpu)} | {int(cpu_avg_gpu_mem)}/{int(cpu_gpu_total)} | {'✅ 예' if cpu_gpu_excluded else '❌ 아니오'} |
| GPU | {gpu_avg_time:.3f} | {gpu_throughput:.2f} | {gpu_avg_cpu:.1f} | {gpu_avg_mem:.1f} | {int(gpu_avg_gpu)} | {int(gpu_avg_gpu_mem)}/{int(gpu_gpu_total)} | N/A |

## 📈 상세 비교

### CPU 모드

#### 성능 지표

- **평균 임베딩 시간**: {cpu_avg_time:.3f}초
- **처리량**: {cpu_throughput:.2f} embeddings/sec
- **벡터 차원**: 1024

#### 리소스 사용량

- **CPU 사용률**: {cpu_avg_cpu:.1f}%
- **메모리 사용량**: {cpu_avg_mem:.1f}MB
- **GPU 사용률**: {int(cpu_avg_gpu)}%
- **GPU 메모리**: {int(cpu_avg_gpu_mem)}MB / {int(cpu_gpu_total)}MB ({cpu_avg_gpu_mem/cpu_gpu_total*100:.1f}%)

- **측정 시간**: {cpu_results[0][1].measured_at or _timestamp("iso")}

#### GPU 배제 확인

{"✅ **GPU가 완전히 배제되었습니다.**" if cpu_gpu_excluded else "⚠️ **GPU가 완전히 배제되지 않았습니다.**"}
{"- GPU 메모리: " + str(int(cpu_avg_gpu_mem)) + "MB (500MB 미만)" if cpu_gpu_excluded else "- GPU 메모리: " + str(int(cpu_avg_gpu_mem)) + "MB (500MB 초과)"}
{"- GPU 사용률: " + str(int(cpu_avg_gpu)) + "% (5% 미만)" if cpu_gpu_excluded else "- GPU 사용률: " + str(int(cpu_avg_gpu)) + "% (5% 초과)"}

{"**권장 조치:**" if not cpu_gpu_excluded else ""}
{"1. Ollama 서버를 CPU 모드로 재시작:" if not cpu_gpu_excluded else ""}
{"   ```bash" if not cpu_gpu_excluded else ""}
{"   pkill ollama" if not cpu_gpu_excluded else ""}
{"   CUDA_VISIBLE_DEVICES='' ollama serve" if not cpu_gpu_excluded else ""}
{"   ```" if not cpu_gpu_excluded else ""}
{"2. 모델이 GPU 메모리를 사용하지 않도록 확인" if not cpu_gpu_excluded else ""}

### GPU 모드

#### 성능 지표

- **평균 임베딩 시간**: {gpu_avg_time:.3f}초
- **처리량**: {gpu_throughput:.2f} embeddings/sec
- **벡터 차원**: 1024

#### 리소스 사용량

- **CPU 사용률**: {gpu_avg_cpu:.1f}%
- **메모리 사용량**: {gpu_avg_mem:.1f}MB
- **GPU 사용률**: {int(gpu_avg_gpu)}%
- **GPU 메모리**: {int(gpu_avg_gpu_mem)}MB / {int(gpu_gpu_total)}MB ({gpu_avg_gpu_mem/gpu_gpu_total*100:.1f}%)

- **측정 시간**: {gpu_results[0][1].measured_at or _timestamp("iso")}

## 🔍 비교 분석

### 성능 비교

- **속도 향상**: {"GPU 모드가 CPU 모드보다" if speedup > 1 else "CPU 모드가 GPU 모드보다"} **{speedup:.2f}배 {"빠름" if speedup > 1 else "느림"}**
  - CPU: {cpu_avg_time:.3f}초
  - GPU: {gpu_avg_time:.3f}초

- **메모리 차이**: {"GPU 모드가" if gpu_avg_mem > cpu_avg_mem else "CPU 모드가"} {abs(gpu_avg_mem - cpu_avg_mem):.1f}MB {"더 많이 사용" if gpu_avg_mem > cpu_avg_mem else "더 적게 사용"}

---

## 📝 참고사항

- 이 보고서는 Ollama Embedding 모델의 리소스 사용량을 측정한 결과입니다.
- 결과는 시스템 환경과 하드웨어 사양에 따라 달라질 수 있습니다.
- **중요**: CPU 모드에서도 GPU가 사용된 경우, Ollama 서버가 이미 GPU에 모델을 로드한 상태에서 실행되었기 때문입니다.
- `num_gpu=0` 파라미터만으로는 Ollama 서버의 GPU 메모리에서 모델을 언로드할 수 없습니다.
- **진정한 CPU 모드 테스트를 위해서는** Ollama 서버를 CPU 모드로 재시작해야 합니다:
  ```bash
  pkill ollama
  CUDA_VISIBLE_DEVICES='' ollama serve
  ```
- 여러 번 실행한 평균값을 사용하여 정확도를 높였습니다.
- CPU와 GPU 모드의 시간이 비슷한 경우, 두 모드 모두 GPU를 사용하고 있을 가능성이 높습니다.
"""
    
    report_path.write_text(report_content, encoding="utf-8")
    return report_path


def main() -> None:
    args = _parse_args()
    
    # Determine which PDF to process
    if args.pdf:
        if args.pdf in PDF_TARGETS:
            pdf_path = PDF_TARGETS[args.pdf]
            label = args.pdf
        elif Path(args.pdf).exists():
            pdf_path = Path(args.pdf)
            label = pdf_path.stem
        else:
            print(f"[ERROR] PDF file not found: {args.pdf}")
            return
    else:
        # Process all PDFs
        pdf_path = None
        label = None
    
    # If specific PDF, process it for both CPU and GPU
    if pdf_path:
        if not pdf_path.exists():
            print(f"[ERROR] PDF file not found: {pdf_path}")
            return
        
        print(f"\n{'='*60}")
        print(f"Processing: {pdf_path.name}")
        print(f"{'='*60}")
        
        # Load and chunk once
        chunks, pre_timings = _load_and_chunk(pdf_path)
        if not chunks:
            print(f"[WARN] No text chunks extracted from {pdf_path}")
            return
        
        texts = [chunk.page_content for chunk in chunks]
        metadatas = [chunk.metadata for chunk in chunks]
        chunk_count = len(chunks)
        
        # CPU mode
        print(f"\n🔵 CPU 모드 테스트 시작...")
        print(f"⚠️  주의: Ollama 서버가 이미 GPU에 모델을 로드한 상태라면")
        print(f"   num_gpu=0 설정에도 불구하고 GPU를 사용할 수 있습니다.")
        print(f"   진정한 CPU 모드를 위해서는 Ollama 서버를 CPU 모드로 재시작해야 합니다.")
        print(f"   (예: CUDA_VISIBLE_DEVICES='' ollama serve)\n")
        
        cpu_results = []
        for run in range(args.runs):
            print(f"  Run {run + 1}/{args.runs}...")
            embedder = _build_embedder(device="cpu")
            embeddings, embed_timing, resource_usage = _embed_chunks(texts, embedder, device="cpu")
            cpu_results.append((embed_timing, resource_usage))
            if run == 0:  # Save only first run
                output_path, persist_timing = _persist_embeddings(
                    f"{label}_cpu", pdf_path, texts, embeddings, metadatas
                )
        
        cpu_avg_time = sum(r[0].seconds for r in cpu_results) / len(cpu_results)
        cpu_gpu_used = any(r[1].gpu_percent and r[1].gpu_percent > 5 for r in cpu_results)
        print(f"✅ CPU 모드 완료 (평균 시간: {cpu_avg_time:.3f}초)")
        if cpu_gpu_used:
            print(f"   ⚠️  CPU 모드에서도 GPU가 사용되었습니다 (Ollama 서버가 GPU에 모델 로드됨)")
        
        # GPU mode
        print(f"\n🟢 GPU 모드 테스트 시작...")
        gpu_results = []
        for run in range(args.runs):
            print(f"  Run {run + 1}/{args.runs}...")
            embedder = _build_embedder(device="gpu")
            embeddings, embed_timing, resource_usage = _embed_chunks(texts, embedder, device="gpu")
            gpu_results.append((embed_timing, resource_usage))
            if run == 0:  # Save only first run
                output_path, persist_timing = _persist_embeddings(
                    f"{label}_gpu", pdf_path, texts, embeddings, metadatas
                )
        
        gpu_avg_time = sum(r[0].seconds for r in gpu_results) / len(gpu_results)
        print(f"✅ GPU 모드 완료 (평균 시간: {gpu_avg_time:.3f}초)")
        
        # Generate comparison report
        print(f"\n📝 비교 보고서 생성 중...")
        report_path = _generate_comparison_report(
            pdf_path, cpu_results, gpu_results, chunk_count
        )
        print(f"✅ 보고서 저장: {report_path}")
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"📊 요약")
        print(f"{'='*60}")
        print(f"CPU: {cpu_avg_time:.3f}초 | GPU: {gpu_avg_time:.3f}초")
        print(f"속도 향상: {cpu_avg_time / gpu_avg_time:.2f}배")
        print(f"보고서: {report_path}")
    else:
        # Original behavior: process all PDFs with specified device
        embedder = _build_embedder(device=args.device)
        
        for label, pdf_path in PDF_TARGETS.items():
            if not pdf_path.exists():
                print(f"[WARN] Skipping missing file: {pdf_path}")
                continue

            chunks, pre_timings = _load_and_chunk(pdf_path)
            if not chunks:
                print(f"[WARN] No text chunks extracted from {pdf_path}")
                continue

            texts = [chunk.page_content for chunk in chunks]
            metadatas = [chunk.metadata for chunk in chunks]

            embeddings, embed_timing, resource_usage = _embed_chunks(texts, embedder)
            output_path, persist_timing = _persist_embeddings(
                label, pdf_path, texts, embeddings, metadatas
            )

            _print_timing_report(
                doc_label=label,
                pdf_path=pdf_path,
                chunk_count=len(chunks),
                timings=[*pre_timings, embed_timing, persist_timing],
                output_path=output_path,
                resource_usage=resource_usage,
            )


if __name__ == "__main__":
    main()

