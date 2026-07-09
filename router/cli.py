"""사용법:
  python -m router.cli "엔비디아 최신 뉴스"            # 실제 호출 (.env 키 필요)
  python -m router.cli "테스트 주제" --dry-run        # 키 없이 구조 테스트
  python -m router.cli "주제" --task plan             # 기획 작업으로 라우팅
"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from router.router import route
from agents.writer import MissingKeyError

def main():
    p = argparse.ArgumentParser()
    p.add_argument("prompt")
    p.add_argument("--task", default="script")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    try:
        out = route(a.task, a.prompt, dry_run=a.dry_run)
    except MissingKeyError as e:
        print(f"⚠ {e}"); sys.exit(1)
    u = out["usage"]
    print(out["result"]["text"])
    print("-" * 40)
    cost = f'{u["cost_krw"]}원' if u["cost_krw"] is not None else "미산정(가격 미설정)"
    print(f'[{u["provider"]}/{u["model"]}] 입력 {u["input_tokens"]} / 출력 {u["output_tokens"]} 토큰 · 비용 {cost}')

if __name__ == "__main__":
    main()
