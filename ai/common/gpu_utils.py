"""
EchoShield GPU & CUDA/cuDNN Utilities
======================================
Provides safe initialization for Windows CUDA/cuDNN DLL paths so that
ONNX Runtime GPU and PyTorch can locate cuDNN 9.x, cublas, etc.
"""

import os
from pathlib import Path
import sys

_DLLS_INITIALIZED = False

def setup_nvidia_dll_paths() -> None:
    """
    On Windows with Python 3.8+, DLL dependencies for C-extensions
    must be explicitly added using os.add_dll_directory.
    Register installed CUDA and cuDNN binaries from the active environment.
    """
    global _DLLS_INITIALIZED
    if _DLLS_INITIALIZED or sys.platform != "win32":
        return

    site_packages_roots = [
        Path(sys.prefix) / "Lib" / "site-packages" / "nvidia",
    ]

    try:
        import site
        if hasattr(site, "getusersitepackages"):
            site_packages_roots.append(Path(site.getusersitepackages()) / "nvidia")
    except Exception:
        pass

    dll_dirs = []
    for root in site_packages_roots:
        if not root.exists():
            continue
        for dll_file in root.rglob("*.dll"):
            parent_dir = dll_file.parent.resolve()
            if parent_dir not in dll_dirs:
                dll_dirs.append(parent_dir)

    for d in dll_dirs:
        try:
            os.add_dll_directory(str(d))
        except (AttributeError, OSError):
            pass
        os.environ["PATH"] = str(d) + os.pathsep + os.environ.get("PATH", "")

    _DLLS_INITIALIZED = True
