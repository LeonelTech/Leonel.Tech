# 🎉 Acervo v0.3.0 - Complete Release

## Features Implemented

### ✅ Step 1: Windows Executable
- Built with PyInstaller (6.9 MB)
- PowerShell installer included
- Ready for distribution
- Location: `dist/Acervo-Install`

### ✅ Step 2: Graph Visualization
- New 🕸️ Grafo tab in web UI
- D3.js force-directed graph
- Interactive node dragging
- Entity relationship visualization

### ✅ Step 3: Audio Transcription (Phase 7)
- New 🎤 Transcrição tab
- OpenAI Whisper integration
- Speaker diarization with VAD
- Multi-language support (PT, EN, ES, etc)

## Test Results
- ✅ 88 tests passing
- ✅ 3 skipped (optional dependencies)
- ✅ 100% backward compatible

## New Endpoints
- `POST /api/transcription` - Convert audio to text
- `POST /api/diarization` - Detect speakers

## Download
- `Leonel.Tech-Complete.zip` (17 MB)
- `Leonel.Tech-Complete.tar.gz` (16 MB)

## Files Modified/Added
- `acervo/services/transcription.py` (NEW)
- `acervo/api/routes.py` (+95 lines)
- `acervo/api/schemas.py` (+44 lines)
- `acervo/web/index.html` (+250 lines)
- `tests/test_transcription.py` (NEW)

## Installation

```bash
# From ZIP
unzip Leonel.Tech-Complete.zip
cd Leonel.Tech
pip install -r requirements.txt
python -m acervo.main
```

## Usage
- Access: http://127.0.0.1:8787
- 6 functional tabs
- 20+ REST endpoints
- Full Portuguese + English support

---
**Release Date:** 2026-07-15
**Status:** ✅ Production Ready
