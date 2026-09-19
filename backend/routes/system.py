"""
System Health & Hardware Telemetry Endpoint for Dhwani / EchoShield AI
Returns live GPU (RTX 5060), VRAM, active models, and backend readiness.
"""

from datetime import datetime, timezone
import os
import ctypes
import os
import torch
from fastapi import APIRouter
from backend.services.detector import _AASIST_MODEL, _AASIST_L_MODEL, _ACOUSTIC_MODEL, _W2V2_MODEL, _SPEAKER_ENGINE

router = APIRouter(tags=["System"])


def _get_system_memory() -> dict:
    """Retrieve system RAM usage on Windows using ctypes without third-party dependencies."""
    try:
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))

        total_mb = round(stat.ullTotalPhys / (1024**2), 1)
        avail_mb = round(stat.ullAvailPhys / (1024**2), 1)
        used_mb = round(total_mb - avail_mb, 1)

        return {
            "ram_used_mb": used_mb,
            "ram_total_mb": total_mb,
            "ram_percent": stat.dwMemoryLoad,
            "cpu_status": "NORMAL",
        }
    except Exception:
        return {"ram_status": "AVAILABLE", "cpu_status": "NORMAL"}


@router.get("/system/status")
async def get_system_status():
    """
    Detailed hardware and model health telemetry for the Dhwani dashboard.
    """
    cuda_available = torch.cuda.is_available()
    gpu_info = {}
    if cuda_available:
        try:
            device_name = torch.cuda.get_device_name(0)
            allocated = round(torch.cuda.memory_allocated(0) / (1024**2), 2)
            reserved = round(torch.cuda.memory_reserved(0) / (1024**2), 2)
            total_vram = round(torch.cuda.get_device_properties(0).total_memory / (1024**2), 2)
            gpu_info = {
                "device_name": device_name,
                "vram_allocated_mb": allocated,
                "vram_reserved_mb": reserved,
                "vram_total_mb": total_vram,
                "utilization_percent": round((reserved / total_vram) * 100, 1) if total_vram else 0,
            }
        except Exception:
            gpu_info = {"device_name": "NVIDIA GPU", "status": "active"}
    else:
        gpu_info = {"status": "cpu_fallback"}

    # Process and system RAM
    ram_info = _get_system_memory()


    active_detectors = []
    if _W2V2_MODEL:
        active_detectors.append({"model": "W2V2-AASIST", "type": "Self-Supervised Wav2Vec2 + GAT", "device": "CUDAExecutionProvider", "status": "ONLINE"})
    if _AASIST_MODEL:
        active_detectors.append({"model": "AASIST", "type": "Raw Waveform SincNet + GAT", "device": "CUDAExecutionProvider", "status": "ONLINE"})
    if _AASIST_L_MODEL:
        active_detectors.append({"model": "AASIST-L", "type": "Lightweight GAT", "device": "CUDAExecutionProvider", "status": "ONLINE"})
    if _ACOUSTIC_MODEL:
        active_detectors.append({"model": "ACOUSTIC", "type": "Handcrafted Spectral/LFCC", "device": "CPU", "status": "ONLINE"})
    if _SPEAKER_ENGINE:
        active_detectors.append({"model": "ECAPA-TDNN", "type": "Deep Speaker Identity Verification", "device": "CUDAExecutionProvider", "status": "ONLINE"})

    return {
        "service": "dhwani-backend",
        "status": "OPERATIONAL",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gpu": gpu_info,
        "system": ram_info,
        "active_models": active_detectors,
        "pipeline": {
            "sample_rate": 16000,
            "window_size": 64600,
            "window_duration_sec": 4.0375,
            "hop_size": 16000,
            "vad_gate": "ENABLED",
        },
    }
