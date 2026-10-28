"""
Dataset Manifest Loader & Audio Validation Engine for Dhwani Evaluation Framework
==================================================================================
Provides decoupled, manifest-driven dataset ingestion, label canonicalization,
audio validation, and duplicate detection without embedding hardcoded dataset paths.
"""

import csv
from dataclasses import dataclass, field
import hashlib
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import numpy as np
import soundfile as sf


BONAFIDE_LABELS: Set[str] = {"bonafide", "bona-fide", "bona_fide", "genuine", "real", "0"}
SPOOF_LABELS: Set[str] = {"spoof", "fake", "synthetic", "clone", "attack", "1"}


class LabelCanonicalizer:
    """Standardizes heterogeneous dataset labels into canonical binary categories."""

    @staticmethod
    def canonicalize(raw_label: Any) -> str:
        """
        Convert raw label string/int into 'bonafide' or 'spoof'.
        Raises ValueError on ambiguous or unsupported labels.
        """
        if raw_label is None:
            raise ValueError("Label cannot be None.")

        cleaned = str(raw_label).strip().lower()
        if cleaned in BONAFIDE_LABELS:
            return "bonafide"
        if cleaned in SPOOF_LABELS:
            return "spoof"

        valid_options = sorted(list(BONAFIDE_LABELS | SPOOF_LABELS))
        raise ValueError(
            f"Unsupported or ambiguous label: '{raw_label}'. "
            f"Must be one of the documented canonical forms: {valid_options}"
        )

    @staticmethod
    def label_to_binary(label: str) -> int:
        """Map canonical string label to binary target (spoof=1, bonafide=0)."""
        canon = LabelCanonicalizer.canonicalize(label)
        return 1 if canon == "spoof" else 0

    @staticmethod
    def binary_to_label(val: int) -> str:
        """Map binary target (1 -> 'spoof', 0 -> 'bonafide')."""
        if int(val) == 1:
            return "spoof"
        if int(val) == 0:
            return "bonafide"
        raise ValueError(f"Binary target must be 0 or 1, got {val}")


@dataclass
class ManifestRecord:
    """Represents a validated audio record from an evaluation manifest."""
    audio_path: Path
    label: str  # Canonical 'bonafide' or 'spoof'
    binary_label: int  # 0 = bonafide, 1 = spoof
    speaker_id: Optional[str] = None
    attack_type: Optional[str] = None
    subset: Optional[str] = None
    duration_sec: Optional[float] = None
    sample_rate: Optional[int] = None
    content_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AudioValidator:
    """Validates audio file integrity, headers, readability, and numerical sanity."""

    @staticmethod
    def compute_content_hash(file_path: Union[str, Path]) -> str:
        """Compute SHA-256 hash of audio file contents for duplicate & leakage detection."""
        p = Path(file_path)
        hasher = hashlib.sha256()
        with open(p, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def validate_audio(
        file_path: Union[str, Path],
        expected_sample_rate: Optional[int] = 16000,
        min_duration_sec: float = 0.05,
        max_duration_sec: float = 600.0,
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Inspect and read audio file to ensure compatibility.

        Returns:
            (is_valid: bool, error_msg: Optional[str], info: Optional[Dict])
        """
        p = Path(file_path)
        if not p.is_file():
            return False, f"Audio file does not exist: {p}", None

        if p.stat().st_size < 44:
            return False, f"File too small to contain valid audio header ({p.stat().st_size} bytes)", None

        try:
            content_hash = AudioValidator.compute_content_hash(p)
            with sf.SoundFile(str(p)) as sf_file:
                sr = sf_file.samplerate
                channels = sf_file.channels
                frames = len(sf_file)
                duration = frames / sr if sr > 0 else 0.0

                if duration < min_duration_sec:
                    return False, f"Audio duration too short ({duration:.3f}s < {min_duration_sec}s)", None

                if duration > max_duration_sec:
                    return False, f"Audio duration exceeds maximum ({duration:.2f}s > {max_duration_sec}s)", None

                # Read small slice to verify non-corrupt samples
                samples = sf_file.read(min(frames, 16000), dtype="float32")
                if not np.all(np.isfinite(samples)):
                    return False, "Audio waveform contains non-finite samples (NaN or Inf)", None

                info = {
                    "sample_rate": sr,
                    "channels": channels,
                    "frames": frames,
                    "duration_sec": round(duration, 3),
                    "format": sf_file.format,
                    "subtype": sf_file.subtype,
                    "content_hash": content_hash,
                }
                return True, None, info

        except Exception as exc:
            return False, f"Failed to read audio file with SoundFile: {exc}", None


class DatasetManifestLoader:
    """Loads and validates CSV/TSV dataset manifests for the evaluation pipeline."""

    def __init__(self, dataset_root: Optional[Union[str, Path]] = None, validate_audio: bool = True):
        self.dataset_root = Path(dataset_root).resolve() if dataset_root else None
        self.validate_audio = validate_audio

    def load_manifest(
        self,
        manifest_path: Union[str, Path],
        subset_filter: Optional[str] = None,
    ) -> Tuple[List[ManifestRecord], Dict[str, Any]]:
        """
        Parse manifest, validate paths and labels, and return valid records and error report.
        """
        mpath = Path(manifest_path).resolve()
        if not mpath.is_file():
            raise FileNotFoundError(f"Manifest file not found: {mpath}")

        records: List[ManifestRecord] = []
        invalid_records: List[Dict[str, Any]] = []
        seen_paths: Set[str] = set()
        seen_hashes: Dict[str, str] = {}
        duplicate_records = 0
        duplicate_hashes = 0

        # Detect delimiter (comma or tab)
        with open(mpath, "r", encoding="utf-8-sig") as f:
            sample = f.read(4096)
            f.seek(0)
            delimiter = "\t" if "\t" in sample and "," not in sample else ","
            reader = csv.DictReader(f, delimiter=delimiter)

            if not reader.fieldnames:
                raise ValueError(f"Manifest file {mpath} is empty or has no header.")

            # Identify audio_path column
            path_col = None
            for candidate in ("audio_path", "path", "file_path", "filename", "audio"):
                if candidate in reader.fieldnames:
                    path_col = candidate
                    break

            if not path_col:
                raise ValueError(
                    f"Manifest {mpath} must contain an 'audio_path' or 'path' column. "
                    f"Found columns: {reader.fieldnames}"
                )

            # Identify label column
            label_col = None
            for candidate in ("label", "target", "class", "ground_truth"):
                if candidate in reader.fieldnames:
                    label_col = candidate
                    break

            if not label_col:
                raise ValueError(
                    f"Manifest {mpath} must contain a 'label' column. "
                    f"Found columns: {reader.fieldnames}"
                )

            for line_idx, row in enumerate(reader, start=2):
                raw_path = (row.get(path_col) or "").strip()
                raw_label = (row.get(label_col) or "").strip()

                if not raw_path:
                    invalid_records.append({
                        "line": line_idx,
                        "raw_path": raw_path,
                        "error": "Empty audio path column",
                    })
                    continue

                # Canonicalize label
                try:
                    canon_label = LabelCanonicalizer.canonicalize(raw_label)
                    binary_label = LabelCanonicalizer.label_to_binary(canon_label)
                except ValueError as val_err:
                    invalid_records.append({
                        "line": line_idx,
                        "raw_path": raw_path,
                        "error": str(val_err),
                    })
                    continue

                # Filter by subset if requested
                row_subset = (row.get("subset") or "").strip().lower()
                if subset_filter and row_subset:
                    if row_subset != subset_filter.strip().lower():
                        continue

                # Resolve path
                p = Path(raw_path)
                if not p.is_absolute():
                    if self.dataset_root is not None:
                        resolved_path = (self.dataset_root / p).resolve()
                    else:
                        cand_manifest = (mpath.parent / p).resolve()
                        cand_cwd = (Path.cwd() / p).resolve()
                        resolved_path = cand_manifest if cand_manifest.is_file() else (cand_cwd if cand_cwd.is_file() else cand_manifest)
                else:
                    resolved_path = p.resolve()

                # Duplicate path check
                str_path = str(resolved_path)
                if str_path in seen_paths:
                    duplicate_records += 1
                seen_paths.add(str_path)

                # Validate audio file
                audio_meta = {}
                duration_sec = None
                sr = None
                c_hash = None
                if self.validate_audio:
                    is_valid, err_msg, info = AudioValidator.validate_audio(resolved_path)
                    if not is_valid:
                        invalid_records.append({
                            "line": line_idx,
                            "raw_path": raw_path,
                            "resolved_path": str(resolved_path),
                            "error": err_msg,
                        })
                        continue
                    audio_meta = info or {}
                    duration_sec = audio_meta.get("duration_sec")
                    sr = audio_meta.get("sample_rate")
                    c_hash = audio_meta.get("content_hash")

                    # Check for duplicate audio content under different filenames
                    if c_hash:
                        if c_hash in seen_hashes and seen_hashes[c_hash] != str_path:
                            duplicate_hashes += 1
                        else:
                            seen_hashes[c_hash] = str_path

                record = ManifestRecord(
                    audio_path=resolved_path,
                    label=canon_label,
                    binary_label=binary_label,
                    speaker_id=row.get("speaker_id"),
                    attack_type=row.get("attack_type"),
                    subset=row_subset or None,
                    duration_sec=duration_sec,
                    sample_rate=sr,
                    content_hash=c_hash,
                    metadata={k: v for k, v in row.items() if k not in (path_col, label_col)},
                )
                records.append(record)

        bonafide_count = sum(1 for r in records if r.label == "bonafide")
        spoof_count = sum(1 for r in records if r.label == "spoof")

        report = {
            "manifest_file": str(mpath),
            "dataset_root": str(self.dataset_root) if self.dataset_root else None,
            "total_rows_evaluated": len(records) + len(invalid_records),
            "valid_records_count": len(records),
            "invalid_records_count": len(invalid_records),
            "bonafide_count": bonafide_count,
            "spoof_count": spoof_count,
            "duplicate_paths_detected": duplicate_records,
            "duplicate_content_hashes_detected": duplicate_hashes,
            "invalid_records": invalid_records,
        }

        return records, report


def verify_split_leakage(
    train_records: List[ManifestRecord],
    val_records: List[ManifestRecord],
    test_records: Optional[List[ManifestRecord]] = None,
) -> Dict[str, Any]:
    """
    Rigorously check for data leakage across dataset partitions (train, validation/dev, test/eval).

    Audits:
    1. Speaker overlap: No speaker ID in train can appear in validation or test partitions.
    2. Path overlap: No exact file path in one partition can exist in another partition.
    3. Content hash overlap: No identical audio file (by SHA-256) can appear in multiple partitions.

    Returns a detailed audit report.
    """
    splits: Dict[str, List[ManifestRecord]] = {
        "train": train_records,
        "val": val_records,
    }
    if test_records is not None:
        splits["test"] = test_records

    leakage_detected = False
    speaker_overlaps: List[Dict[str, Any]] = []
    path_overlaps: List[Dict[str, Any]] = []
    hash_overlaps: List[Dict[str, Any]] = []

    split_names = list(splits.keys())
    for i in range(len(split_names)):
        for j in range(i + 1, len(split_names)):
            s1_name, s2_name = split_names[i], split_names[j]
            s1_recs, s2_recs = splits[s1_name], splits[s2_name]

            # 1. Speaker ID check (exclude None / empty)
            s1_spks = {r.speaker_id for r in s1_recs if r.speaker_id}
            s2_spks = {r.speaker_id for r in s2_recs if r.speaker_id}
            spk_common = s1_spks & s2_spks
            if spk_common:
                leakage_detected = True
                speaker_overlaps.append({
                    "split_pair": f"{s1_name} vs {s2_name}",
                    "overlapping_speaker_count": len(spk_common),
                    "overlapping_speakers": sorted(list(spk_common)),
                })

            # 2. File Path check
            s1_paths = {str(r.audio_path) for r in s1_recs}
            s2_paths = {str(r.audio_path) for r in s2_recs}
            path_common = s1_paths & s2_paths
            if path_common:
                leakage_detected = True
                path_overlaps.append({
                    "split_pair": f"{s1_name} vs {s2_name}",
                    "overlapping_path_count": len(path_common),
                    "overlapping_paths": sorted(list(path_common)),
                })

            # 3. Content hash check (exclude None)
            s1_hashes = {r.content_hash for r in s1_recs if r.content_hash}
            s2_hashes = {r.content_hash for r in s2_recs if r.content_hash}
            hash_common = s1_hashes & s2_hashes
            if hash_common:
                leakage_detected = True
                hash_overlaps.append({
                    "split_pair": f"{s1_name} vs {s2_name}",
                    "overlapping_hash_count": len(hash_common),
                    "overlapping_hashes": sorted(list(hash_common)),
                })

    return {
        "leakage_detected": leakage_detected,
        "splits_evaluated": {name: len(recs) for name, recs in splits.items()},
        "speaker_overlaps": speaker_overlaps,
        "path_overlaps": path_overlaps,
        "hash_overlaps": hash_overlaps,
        "status": "LEAKAGE_DETECTED" if leakage_detected else "LEAKAGE_FREE",
    }
