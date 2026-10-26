"""Spoken examples: one voice message per collocation, read by a German voice.

The recordings are generated ahead of time and committed under `data/audio/`,
so the daily post depends on no speech service. Only cards not yet published
get a recording; once a card is posted its file is no longer needed. A file is named after a hash
of the voice and the sentences: editing an example leaves the old recording
unmatched, and the test suite reports the card as missing its audio.

Regenerate with `python -m bot.audio` (needs `edge-tts` and `ffmpeg`).
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import logging
import os
import shutil
import ssl
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

from . import collocations
from .config import Config
from .state import State

log = logging.getLogger(__name__)

VOICE = "de-DE-KatjaNeural"
SUFFIX = ".ogg"
PAUSE_SECONDS = 1.0


def key(sentences: Sequence[str], voice: str = VOICE) -> str:
    digest = hashlib.sha256("\n".join([voice, *sentences]).encode("utf-8"))
    return digest.hexdigest()[:16]


def path_for(audio_dir: Path, sentences: Sequence[str]) -> Path:
    return audio_dir / f"{key(sentences)}{SUFFIX}"


def find(audio_dir: Path, sentences: Sequence[str]) -> Path | None:
    path = path_for(audio_dir, sentences)
    return path if path.exists() else None


def unpublished(
    store: dict[str, collocations.CollocationCard], posted: Sequence[str]
) -> list[collocations.CollocationCard]:
    done = set(posted)
    return [
        card for phrase, card in store.items() if f"collocation:{phrase}" not in done
    ]


def _ssl_context() -> ssl.SSLContext:
    """edge-tts pins certifi; honour SSL_CERT_FILE for networks behind a proxy."""
    cafile = os.environ.get("SSL_CERT_FILE")
    if cafile:
        return ssl.create_default_context(cafile=cafile)
    import certifi

    return ssl.create_default_context(cafile=certifi.where())


async def _speak(sentence: str, target: Path) -> None:
    import edge_tts.communicate

    edge_tts.communicate._SSL_CTX = _ssl_context()
    await edge_tts.communicate.Communicate(sentence, VOICE).save(str(target))


def synthesize(sentences: Sequence[str], target: Path) -> None:
    """Read each sentence, join them with a pause, encode as OGG Opus.

    Telegram shows OGG Opus sent with sendVoice as a voice message with a
    waveform and playback speed control.
    """
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required to encode the recordings.")
    with tempfile.TemporaryDirectory() as tmp:
        parts = []
        for i, sentence in enumerate(sentences):
            part = Path(tmp) / f"{i}.mp3"
            asyncio.run(_speak(sentence, part))
            parts.append(part)

        inputs: list[str] = []
        streams = ""
        for i, part in enumerate(parts):
            inputs += ["-i", str(part)]
            streams += f"[{i}:a]"
            if i < len(parts) - 1:
                streams += f"[gap{i}]"
        gaps = "".join(
            f"anullsrc=r=24000:cl=mono,atrim=0:{PAUSE_SECONDS}[gap{i}];"
            for i in range(len(parts) - 1)
        )
        count = 2 * len(parts) - 1
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "ffmpeg", "-loglevel", "error", "-y", *inputs,
                "-filter_complex", f"{gaps}{streams}concat=n={count}:v=0:a=1[out]",
                "-map", "[out]", "-ac", "1", "-c:a", "libopus", "-b:a", "32k",
                str(target),
            ],
            check=True,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m bot.audio",
        description=(
            "Record examples of unpublished collocations and remove "
            "recordings no unpublished card uses."
        ),
    )
    parser.add_argument(
        "--check", action="store_true", help="Only report; fail if a recording is missing."
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    config = Config.from_env()
    store = collocations.load(config.collocations_file)
    wanted = {
        path_for(config.audio_dir, card.beispiele): card
        for card in unpublished(store, State.load(config.state_file).posted)
    }
    existing = set(config.audio_dir.glob(f"*{SUFFIX}"))
    missing = [path for path in wanted if path not in existing]
    unused = sorted(existing - set(wanted))

    if args.check:
        for path in missing:
            log.error("Missing audio for %r: %s", wanted[path].ausdruck, path.name)
        # A file goes unused every time its card is posted; that is no error.
        for path in unused:
            log.info("Unused audio: %s", path.name)
        return 1 if missing else 0

    for path in missing:
        log.info("Recording %r → %s", wanted[path].ausdruck, path.name)
        synthesize(wanted[path].beispiele, path)
    for path in unused:
        log.info("Removing unused %s", path.name)
        path.unlink()
    log.info(
        "%d recorded, %d removed, %d unpublished cards.", len(missing), len(unused), len(wanted)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
