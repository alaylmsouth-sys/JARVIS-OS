"""video/editor.py — FFmpeg 편집: 클립 연결 + 음성 + 한글 자막 번인."""
from __future__ import annotations
import subprocess
from pathlib import Path


def _srt(scenes: dict, out: Path) -> Path:
    def ts(sec: float) -> str:
        h, m = divmod(int(sec) // 60, 60)
        s = int(sec) % 60
        ms = int((sec - int(sec)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    lines, t, i = [], 0.0, 1
    hook_end = min(3.0, scenes["scenes"][0]["seconds"])
    lines += [f"{i}", f"{ts(0)} --> {ts(hook_end)}", scenes["hook"], ""]
    i += 1
    for sc in scenes["scenes"]:
        start = t if sc["n"] > 1 else hook_end
        t += sc["seconds"]
        lines += [f"{i}", f"{ts(start)} --> {ts(t)}", sc["narration"], ""]
        i += 1
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def assemble(clips: list[Path], audio: Path, scenes: dict, job_dir: Path) -> Path:
    # 1) 클립 연결
    lst = job_dir / "concat.txt"
    lst.write_text("\n".join(f"file '{c.name}'" for c in clips), encoding="utf-8")
    joined = job_dir / "joined.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat",
                    "-safe", "0", "-i", str(lst), "-c", "copy", str(joined)],
                   check=True, cwd=job_dir)
    # 2) 자막 + 음성
    srt = _srt(scenes, job_dir / "subtitles.srt")
    final = job_dir / "final.mp4"
    style = "FontName=Noto Sans CJK KR,FontSize=15,Outline=1,MarginV=60"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-i", str(joined), "-i", str(audio),
         "-vf", f"subtitles={srt.name}:force_style='{style}'",
         "-af", "apad",  # 나레이션이 영상보다 짧으면 무음 패딩 (영상 길이 유지)
         "-map", "0:v", "-map", "1:a", "-shortest",
         "-c:v", "libx264", "-preset", "fast", "-c:a", "aac", str(final)],
        check=True, cwd=job_dir)
    return final
