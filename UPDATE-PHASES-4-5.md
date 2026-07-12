# Acervo v0.3.0 — Fases 4 & 5 MVP (OCR + Multimedia)

Data: julho de 2026

## O que é novo

Implementadas as arquiteturas e serviços para **Fase 4 (Documents & OCR)** e **Fase 5 (Multimedia & Transcription)**, com testes e schema de banco de dados completos.

### Phase 4 — Documents & OCR ✅

**Arquivos adicionados:**
- `acervo/domain/ocr.py` — Domain models (OcrMethod, TextConfidence, TextRegion, OcrResult)
- `acervo/services/ocr.py` — Adapters e serviços
- `tests/test_ocr.py` — Testes para OCR e detecção legal

**Funcionalidades:**
- ✅ Native PDF extraction (via pypdf se disponível)
- ✅ Tesseract adapter (OCR de imagens)
- ✅ PaddleOCR adapter (OCR local, recomendado)
- ✅ Detecção de CNJ process numbers (LEGAL-001)
- ✅ Detecção de CPF, CNPJ, OAB
- ✅ Bounding boxes + confidence levels
- ✅ Marcadores `[illegible]`, `[partially legible]`

**Banco de dados:**
- `ocr_results` — Um resultado por arquivo
- `ocr_regions` — Regiões extraídas com bbox
- `ocr_corrections` — Audit trail de correções humanas

**Como usar:**
```python
from acervo.services.ocr import NativePdfAdapter, PaddleOcrAdapter

adapter = NativePdfAdapter()  # ou PaddleOcrAdapter()
result = adapter.process("document.pdf", language="por")
print(result.full_text)
for region in result.regions:
    print(f"  - {region.confidence}: {region.text}")
```

---

### Phase 5 — Multimedia & Transcription ✅

**Arquivos adicionados:**
- `acervo/domain/multimedia.py` — Domain models (TranscriptMethod, TranscriptSegment, AudioMetadata…)
- `acervo/services/multimedia.py` — Adapters, inspectors, extractors
- `tests/test_multimedia.py` — Testes para multimedia

**Funcionalidades:**
- ✅ MediaInspector via FFprobe (inspeciona sem processar)
- ✅ AudioExtractor (extrai áudio de vídeos, normaliza para 16kHz)
- ✅ FasterWhisperAdapter (transcription local, recomendado)
- ✅ FrameExtractor (keyframes + timestamps)
- ✅ Suporte a diarization (speaker detection) com rótulos neutros (SPEAKER-001…)
- ✅ Speaker identity mapping com reviewed_as + audit trail (AV-006)
- ✅ Visual descriptions (prep para IA externa)

**Banco de dados:**
- `transcript_results` — Um resultado por arquivo de áudio/vídeo
- `transcript_segments` — Segmentos com timestamps
- `speakers` — Mapeamento speaker → identidade humana confirmada
- `frames` — Keyframes extraídos com metadados
- `visual_descriptions` — Descrições de cenas/quadros

**Como usar:**
```python
from acervo.services.multimedia import (
    MediaInspector, FasterWhisperAdapter, AudioExtractor
)

# Inspecionar arquivo de mídia
metadata = MediaInspector.extract_audio_metadata("video.mp4")
print(f"Duration: {metadata.duration_seconds}s")

# Extrair áudio
AudioExtractor.extract_audio("video.mp4", "extracted_audio.wav")

# Transcrever
adapter = FasterWhisperAdapter()
result = adapter.transcribe("extracted_audio.wav", language="pt")
for segment in result.segments:
    print(f"{segment.start_seconds:.2f}-{segment.end_seconds:.2f}: {segment.text}")
```

---

## Testes adicionados

- **test_ocr.py** (7 testes)
  - Adaptadores disponíveis
  - Detecção de CNJ numbers
  - Detecção de CPF/CNPJ/OAB
  - Confidence levels

- **test_multimedia.py** (6 testes)
  - MediaInspector
  - AudioExtractor
  - FrameExtractor
  - FasterWhisperAdapter
  - TranscriptSegment e TranscriptResult

**Total de testes:** 25 (preservação) + 13 (OCR + multimedia) = **38 testes** ✅

---

## O que ainda precisa fazer (backlog refinado)

### Phase 4 — pendente
- [ ] UI para visualizar regiões OCR com bounding boxes
- [ ] UI para correção manual de OCR
- [ ] Classificação automática de tipo de documento (pleading, decision…)
- [ ] Integração com state machine (METADATA_EXTRACTED → CLASSIFIED → CONTENT_PROCESSED)

### Phase 5 — pendente
- [ ] UI para review de speaker diarization
- [ ] Visual descriptions com IA (local ou externa)
- [ ] Gallery com frames e transcript timeline integrado
- [ ] Playback audio/vídeo com navegação por timestamp

### Phase 6 — Dossiers (próximo?)
- [ ] Entity model (people, lawyers, firms, proceedings…)
- [ ] Assertion/provenance table
- [ ] Cross-reference linking
- [ ] Dossier views

---

## Roadmap atualizado

```
✅ Fase 1    — Foundation
✅ Fase 2    — Preservation
✅ Fase 3    — Catalog Core (partial)
✅ Fase 4    — Documents & OCR (MVP)
✅ Fase 5    — Multimedia & Transcription (MVP)
⏳ Fase 6    — Dossiers & Cross-reference
⏳ Fase 7    — External AI Fallback
⏳ Fase 8    — Integrity & Advanced Review
✅ Fase 9    — Professional Hardening (instalador Windows)
```

---

## Próximos passos

Qual fase implementar?

1. **Fase 6 (Dossiers)** — Entidades e cross-referência (o coração da catalogação)
2. **Fase 3 Expansion** — UI de catálogo avançada (filtragem, bulk actions…)
3. **Fase 7 (AI)** — Fallback para OpenAI (com consent + receipts)
4. **Fase 8 (Integrity)** — Análise de anomalias técnicas

---

Criado em julho de 2026 — Acervo v0.3.0
