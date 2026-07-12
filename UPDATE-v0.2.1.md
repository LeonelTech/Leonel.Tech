# Acervo v0.2.1 — Atualização: Instalador Windows Automático

Data: julho de 2026

## O que é novo

### ✅ Instalador Windows com um clique
Adicionado à **Fase 9 (Professional Hardening)** do roadmap:

- 📦 `installers/INSTALAR.bat` — executável que automatiza tudo
- ⚙️ `installers/acervo-install.ps1` — script PowerShell com toda a lógica
- 🔨 `installers/build_exe.py` — compila um `Acervo-Install.exe` profissional
- 📖 `installers/INSTALE-WINDOWS.md` — guia completo de instalação

## Como usar

### Opção 1: Instalador automático (mais fácil)

1. **Baixe e extraia** o repositório
2. **Clique duas vezes em** `installers/INSTALAR.bat`
3. **Escolha o idioma** (1 = Português, 2 = English)
4. **Aguarde** 3-5 minutos
5. **Pronto!** O servidor web abre automaticamente

O instalador faz automaticamente:
- ✅ Verifica/instala Python 3.11+
- ✅ Cria ambiente virtual isolado
- ✅ Instala SQLAlchemy, FastAPI, Pydantic, etc.
- ✅ Cria atalho no Desktop
- ✅ Inicia o servidor em http://127.0.0.1:8787

### Opção 2: Criar um executável `.exe`

Se quiser distribuir um arquivo único:

```bash
pip install pyinstaller
python installers/build_exe.py
```

Gera: `dist/Acervo-Install.exe` (~50-80 MB)

Usuários finais clicam uma vez e tudo funciona — sem terminal, sem PowerShell.

---

## Documentação adicionada

| Arquivo | Conteúdo |
|---------|----------|
| `LEIA-ME.txt` | Passo a passo em português (terminal) |
| `installers/INSTALE-WINDOWS.md` | Guia de instalação Windows (3 métodos) |
| `installers/README.md` | Documentação técnica do instalador |

---

## Mudanças na aplicação core

**Nenhuma.** A Fase 1 + 2 permanece igual. Apenas adicionados scripts de instalação.

---

## Roadmap atualizado

```
✅ Fase 1    — Foundation (✓ concluída)
✅ Fase 2    — Preservation (✓ core concluída)
⏳ Fase 3    — Catalog Core
⏳ Fase 4    — Documents & OCR
⏳ Fase 5    — Multimedia & Transcription
⏳ Fase 6    — Dossiers & Cross-reference
⏳ Fase 7    — External AI Fallback
⏳ Fase 8    — Integrity & Advanced Review
✅ Fase 9    — Professional Hardening (✓ MVP: instalador Windows)
```

---

## Próximas prioridades

Qual fase devo implementar?

1. **Fase 4 (OCR)** — PDF nativo + Tesseract/PaddleOCR
2. **Fase 5 (Transcription)** — faster-whisper + diarização
3. **Fase 6 (Dossiers)** — Entidades e cross-referência
4. **Fase 3 (Catalog UI)** — Interface de catálogo avançada

---

## Teste rápido

**No Windows (dois cliques):**
```
installers\INSTALAR.bat
```

**Na linha de comando (manual):**
```bash
pip install -r requirements.txt
python -m acervo.cli serve
```

---

Criado em julho de 2026 — Acervo v0.2.1
