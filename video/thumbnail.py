"""video/thumbnail.py — 대표 프레임 추출 + 제목 오버레이."""
from __future__ import annotations
import subprocess
from pathlib import Path

FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"


def create(video: Path, title: str, job_dir: Path) -> Path:
    out = job_dir / "thumbnail.jpg"
    tf = job_dir / "thumb_title.txt"
    tf.write_text(title, encoding="utf-8")
    draw = (f",drawtext=textfile='{tf.name}':fontfile='{FONT}':fontsize=64:"
            f"fontcolor=white:borderw=4:bordercolor=black:"
            f"x=(w-text_w)/2:y=h-text_h-160"
            if Path(FONT).exists() else "")
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video),
         "-ss", "1", "-vframes", "1",
         "-vf", f"scale=1080:-1{draw}", str(out)],
        check=True, cwd=job_dir)
    tf.unlink(missing_ok=True)
    return out
