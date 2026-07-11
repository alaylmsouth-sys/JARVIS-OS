"""음성 모듈 테스트. 실행: python tests/test_voice.py"""
import sys, wave
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from video.voice import pcm_to_wav, _parse_rate, generate

def main(tmp=Path("/tmp/jarvis_voice_test")):
    tmp.mkdir(exist_ok=True)

    # 1. PCM→WAV 래퍼: 24000Hz 16bit 모노 1초(48000바이트) → 정확한 WAV
    pcm = b"\x00\x01" * 24000
    out = pcm_to_wav(pcm, tmp / "t.wav", 24000)
    with wave.open(str(out)) as w:
        assert w.getframerate() == 24000 and w.getnchannels() == 1
        assert abs(w.getnframes() / w.getframerate() - 1.0) < 0.01

    # 2. mime rate 파싱
    assert _parse_rate("audio/L16;codec=pcm;rate=24000") == 24000
    assert _parse_rate("audio/L16") == 24000  # 기본값

    # 3. silent provider는 여전히 동작
    p = generate("테스트", 2, {"provider": "silent"}, tmp)
    assert p.exists() and p.stat().st_size > 0

    # 4. 알 수 없는 provider 거부
    try:
        generate("x", 1, {"provider": "없는것"}, tmp); raise AssertionError
    except ValueError:
        pass

    print("✅ 음성 모듈 테스트 4/4 통과")

if __name__ == "__main__":
    main()
