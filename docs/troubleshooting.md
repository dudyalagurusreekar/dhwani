# Troubleshooting & FAQ Guide for Dhwani

---

## 1. CUDA & GPU Issues

### Error: `CUDAExecutionProvider not available`
- **Cause**: PyTorch or ONNX Runtime is using CPU fallback.
- **Solution**: Ensure NVIDIA CUDA 12.8 drivers are installed and `ai.common.gpu_utils.setup_nvidia_dll_paths()` is called at application startup. Verify with:
  ```powershell
  python -c "import torch; print('CUDA Available:', torch.cuda.is_available(), 'Device:', torch.cuda.get_device_name(0))"
  ```

---

## 2. Telephony & WebSocket Issues

### Error: `Twilio WebSocket Connection Refused`
- **Cause**: The public URL configured in Twilio Console does not point to an active ngrok tunnel, or Dhwani backend is not running on port 8000.
- **Solution**:
  1. Verify Uvicorn is running: `python -m uvicorn backend.main:app --port 8000`
  2. Verify ngrok tunnel is active: `ngrok http 8000`
  3. Ensure `TWILIO_STREAM_PUBLIC_URL` in `.env` uses `wss://` protocol.

---

## 3. High Spoof Scores on Background Silence

### Solution:
Dhwani includes an Energy VAD Pre-Filter (`streaming/vad_gate.py`) operating at `-38 dBFS`. Windows lacking valid voiced human speech are automatically marked `NO_SPEECH` and bypass the deep neural models completely. If your room is very noisy, adjust:
```python
vad = EnergyVADGate(energy_threshold_db=-32.0, active_frame_ratio_threshold=0.25)
```

---

## 4. Frontend Build & Node.js

### Error: `Module not found` in Next.js
- **Solution**: Run `npm install` inside `frontend/` directory to ensure all dependencies (`lucide-react`, `recharts`, `three`) are resolved.
