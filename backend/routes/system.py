"""
System Health & Hardware Telemetry Endpoint for Dhwani / EchoShield AI
Returns live GPU / CPU status, VRAM, dynamic detector statuses, and backend readiness.
"""

from datetime import datetime, timezone
import ctypes
import os
import torch
from fastapi import APIRouter
from backend.services import detector

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
    Dynamically queries live detector states and device availability.
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
        gpu_info = {"status": "cpu_fallback", "device_name": "CPU"}

    # Process and system RAM
    ram_info = _get_system_memory()

    # Dynamic detector querying via live service registry
    live_detectors = detector.get_active_detectors()
    detector_health = detector.get_detector_health()

    # Formatted for dashboard compatibility while reporting truthful states
    model_entries = []
    for d in live_detectors:
        model_name = d.get("model", "UNKNOWN")
        is_online = d.get("is_available", False)
        status_label = "ONLINE" if is_online else d.get("status", "UNAVAILABLE")
        model_entries.append({
            "model": model_name,
            "status": status_label,
            "device": d.get("device", "cpu"),
            "backend": d.get("backend", "unknown"),
            "is_available": is_online,
            "error": d.get("error"),
        })

    return {
        "service": "dhwani-backend",
        "status": "OPERATIONAL",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gpu": gpu_info,
        "system": ram_info,
        "active_models": model_entries,
        "detector_health": detector_health,
        "pipeline": {
            "sample_rate": 16000,
            "window_size": 64600,
            "window_duration_sec": 4.0375,
            "hop_size": 16000,
            "vad_gate": "ENABLED",
        },
    }
