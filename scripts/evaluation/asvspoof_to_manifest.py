"""
ASVspoof Protocol to Dhwani Manifest Converter
=============================================
Converts official ASVspoof 2019 / 2021 Logical Access (LA) protocol text files
into standard Dhwani CSV manifests with explicit metadata and verified paths.
"""

import argparse
import csv
from pathlib import Path
import sys
from typing import Optional


def convert_asvspoof_protocol(
    protocol_file: Path,
    audio_dir: Path,
    output_manifest: Path,
    subset_name: Optional[str] = None,
    audio_ext: str = ".flac",
) -> int:
    """
    Parse ASVspoof protocol file and generate standard CSV manifest.

    ASVspoof protocol format:
    <speaker_id> <filename> <environment> <attack_type> <key>
    e.g.:
    LA_0069 LA_D_1047731 - - bonafide
    LA_0069 LA_D_1105538 - A01 spoof
    """
    protocol_path = Path(protocol_file).resolve()
    audio_path = Path(audio_dir).resolve()
    out_path = Path(output_manifest).resolve()

    if not protocol_path.is_file():
        raise FileNotFoundError(f"ASVspoof protocol file not found: {protocol_path}")
    if not audio_path.is_dir():
        raise FileNotFoundError(f"Audio directory not found: {audio_path}")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    missing_count = 0

    with open(protocol_path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 5:
                continue

            speaker_id = parts[0]
            basename = parts[1]
            attack_type = parts[3]
            raw_key = parts[4].lower()

            # Find matching audio file
            candidate = audio_path / f"{basename}{audio_ext}"
            if not candidate.is_file():
                # Try .wav if .flac not found
                alt = audio_path / f"{basename}.wav"
                if alt.is_file():
                    candidate = alt
                else:
                    missing_count += 1

            rel_audio_path = candidate.name if candidate.parent == audio_path else str(candidate)

            rows.append({
                "audio_path": rel_audio_path,
                "label": raw_key,
                "speaker_id": speaker_id,
                "attack_type": attack_type,
                "subset": subset_name or ("eval" if "eval" in protocol_path.name.lower() else "dev"),
            })

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["audio_path", "label", "speaker_id", "attack_type", "subset"],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Successfully converted {len(rows)} protocol records to {out_path}")
    if missing_count > 0:
        print(f"Warning: {missing_count} audio files referenced in protocol were not found on disk.")
    return len(rows)


def main():
    parser = argparse.ArgumentParser(description="Convert ASVspoof protocol to Dhwani CSV manifest")
    parser.add_argument("--protocol-file", required=True, type=Path, help="Path to ASVspoof protocol .txt file")
    parser.add_argument("--audio-dir", required=True, type=Path, help="Directory containing .flac or .wav audio")
    parser.add_argument("--output-manifest", required=True, type=Path, help="Output CSV manifest path")
    parser.add_argument("--subset", default=None, help="Subset identifier (dev, eval, etc.)")
    args = parser.parse_args()

    convert_asvspoof_protocol(
        protocol_file=args.protocol_file,
        audio_dir=args.audio_dir,
        output_manifest=args.output_manifest,
        subset_name=args.subset,
    )


if __name__ == "__main__":
    main()
