"""
MinerU JSON 출력에서 Reference 섹션 추출 및 마크다운 파일에 추가

MinerU는 페이지 하단 30% 영역의 블록을 footnote로 인식하여 제외합니다.
Reference 섹션이 이 영역에 있으면 discarded_blocks에 포함되므로,
이 스크립트를 사용하여 Reference를 추출하고 마크다운 파일에 추가할 수 있습니다.
"""

import json
import re
from pathlib import Path
from typing import List, Optional
from datetime import datetime


def extract_references_from_json(json_path: Path) -> List[str]:
    """
    MinerU JSON 파일에서 Reference 섹션 추출
    
    Args:
        json_path: MinerU가 생성한 _middle.json 파일 경로
    
    Returns:
        Reference 항목 리스트
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    pdf_info = data['pdf_info'][0]
    discarded_blocks = pdf_info.get('discarded_blocks', [])
    
    references = []
    reference_keywords = [
        r'^\d+\.',  # 숫자로 시작 (1., 2., 등)
        'et al',
        'doi:',
        'doi.org',
        'journal',
        'nature',
        'cell',
        'science',
        'proc',
        'res',
        'biol',
        'chem',
    ]
    
    for block in discarded_blocks:
        if 'lines' in block:
            block_lines = []
            for line in block['lines']:
                if 'spans' in line:
                    line_content = ' '.join([s.get('content', '').strip() for s in line['spans']])
                    if line_content:
                        block_lines.append(line_content)
            
            if block_lines:
                # 각 라인을 개별적으로 확인 (Reference는 보통 한 줄에 하나씩)
                full_content = '\n'.join(block_lines)
                
                # Reference 패턴 확인
                is_reference = False
                for keyword in reference_keywords:
                    if isinstance(keyword, str):
                        if keyword.lower() in full_content.lower():
                            is_reference = True
                            break
                    else:  # regex pattern
                        if re.search(keyword, full_content, re.IGNORECASE):
                            is_reference = True
                            break
                
                if is_reference:
                    # 여러 Reference가 하나의 블록에 있을 수 있으므로 줄 단위로 분리
                    # 숫자로 시작하는 줄을 기준으로 분리
                    ref_items = []
                    current_ref = []
                    
                    for line in block_lines:
                        line_stripped = line.strip()
                        # 숫자로 시작하는 줄이면 새로운 Reference 시작
                        if re.match(r'^\d+\.', line_stripped):
                            if current_ref:
                                # 이전 Reference 저장
                                ref_text = ' '.join(current_ref).strip()
                                if ref_text:
                                    ref_items.append(ref_text)
                            current_ref = [line_stripped]
                        elif current_ref:
                            # 현재 Reference에 추가
                            current_ref.append(line_stripped)
                        elif line_stripped:  # Reference 블록 내의 다른 텍스트
                            current_ref.append(line_stripped)
                    
                    # 마지막 Reference 추가
                    if current_ref:
                        ref_text = ' '.join(current_ref).strip()
                        if ref_text:
                            ref_items.append(ref_text)
                    
                    # 분리된 Reference가 있으면 사용, 없으면 전체를 줄 단위로 분리
                    if ref_items:
                        references.extend(ref_items)
                    else:
                        # 줄 단위로 분리 시도
                        for line in block_lines:
                            if line.strip() and re.match(r'^\d+\.', line.strip()):
                                references.append(line.strip())
                        if not references:
                            references.append(full_content)
    
    return references


def add_references_to_markdown(
    md_path: Path,
    json_path: Path,
    backup: bool = True
) -> bool:
    """
    마크다운 파일에 Reference 섹션 추가
    
    Args:
        md_path: 마크다운 파일 경로
        json_path: MinerU JSON 파일 경로
        backup: 원본 파일 백업 여부
    
    Returns:
        성공 여부
    """
    # JSON에서 Reference 추출
    references = extract_references_from_json(json_path)
    
    if not references:
        print(f"⚠️  Reference를 찾을 수 없습니다: {json_path}")
        return False
    
    print(f"✅ {len(references)}개의 Reference 항목 발견")
    
    # 마크다운 파일 읽기
    if not md_path.exists():
        print(f"❌ 마크다운 파일을 찾을 수 없습니다: {md_path}")
        return False
    
    md_content = md_path.read_text(encoding='utf-8')
    
    # 백업 생성
    if backup:
        backup_path = md_path.with_suffix('.md.backup')
        backup_path.write_text(md_content, encoding='utf-8')
        print(f"📋 백업 생성: {backup_path}")
    
    # Reference 섹션 생성
    ref_section = '\n\n'.join(references)
    
    # 기존 Reference 섹션 교체 또는 추가
    if '# References' in md_content or '## References' in md_content:
        # 기존 Reference 섹션 찾아서 교체
        lines = md_content.split('\n')
        new_lines = []
        skip = False
        
        for line in lines:
            if line.strip() == '# References' or line.strip() == '## References':
                new_lines.append('# References')
                new_lines.append('')  # 빈 줄
                new_lines.append(ref_section)
                skip = True
            elif skip:
                # 다음 헤더(#로 시작)를 만나면 스킵 중지
                if line.strip().startswith('#') and not line.strip().startswith('# References'):
                    skip = False
                    new_lines.append(line)
                # 헤더가 아니면 계속 스킵 (빈 줄도 스킵)
            else:
                new_lines.append(line)
        
        md_content = '\n'.join(new_lines)
        print("✅ 기존 Reference 섹션 교체")
    else:
        # 마지막에 Reference 섹션 추가
        md_content += f'\n\n# References\n\n{ref_section}\n'
        print("✅ Reference 섹션 추가")
    
    # 저장
    md_path.write_text(md_content, encoding='utf-8')
    print(f"💾 마크다운 파일 업데이트: {md_path}")
    print(f"📊 추가된 Reference 항목 수: {len(references)}")
    
    return True


def process_mineru_output(output_dir: Path, auto_fix: bool = True):
    """
    MinerU 출력 디렉토리에서 모든 마크다운 파일의 Reference 섹션 수정
    
    Args:
        output_dir: MinerU 출력 디렉토리
        auto_fix: 자동으로 Reference 추가 여부
    """
    md_files = list(output_dir.rglob("*.md"))
    json_files = list(output_dir.rglob("*_middle.json"))
    
    print(f"📁 발견된 마크다운 파일: {len(md_files)}개")
    print(f"📁 발견된 JSON 파일: {len(json_files)}개\n")
    
    fixed_count = 0
    for md_file in md_files:
        # 해당하는 JSON 파일 찾기
        json_file = md_file.parent / md_file.name.replace('.md', '_middle.json')
        
        if not json_file.exists():
            # 다른 패턴 시도
            json_file = md_file.parent / f"{md_file.stem}_middle.json"
        
        if json_file.exists():
            print(f"\n📄 처리 중: {md_file.name}")
            if add_references_to_markdown(md_file, json_file, backup=True):
                fixed_count += 1
        else:
            print(f"⚠️  JSON 파일을 찾을 수 없습니다: {md_file.name}")
    
    print(f"\n✅ 총 {fixed_count}개 파일 수정 완료")


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="MinerU JSON에서 Reference 섹션 추출 및 마크다운 파일에 추가"
    )
    parser.add_argument(
        'md_file',
        type=Path,
        help='마크다운 파일 경로'
    )
    parser.add_argument(
        'json_file',
        type=Path,
        nargs='?',
        help='JSON 파일 경로 (지정하지 않으면 자동으로 찾음)'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        help='MinerU 출력 디렉토리 (지정하면 모든 파일 처리)'
    )
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='백업 파일 생성 안 함'
    )
    
    args = parser.parse_args()
    
    if args.output_dir:
        # 디렉토리 전체 처리
        process_mineru_output(args.output_dir, auto_fix=True)
    else:
        # 단일 파일 처리
        json_file = args.json_file
        if not json_file:
            # 자동으로 찾기
            json_file = args.md_file.parent / args.md_file.name.replace('.md', '_middle.json')
            if not json_file.exists():
                json_file = args.md_file.parent / f"{args.md_file.stem}_middle.json"
        
        if not json_file.exists():
            print(f"❌ JSON 파일을 찾을 수 없습니다: {json_file}")
            return
        
        add_references_to_markdown(
            args.md_file,
            json_file,
            backup=not args.no_backup
        )


if __name__ == "__main__":
    main()

