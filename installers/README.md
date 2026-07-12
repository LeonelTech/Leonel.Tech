# Acervo Installers

Arquivos de instalação para Windows (Fase 9 - Professional Hardening MVP).

## Arquivos incluídos

| Arquivo | Descrição | Como usar |
|---------|-----------|-----------|
| `INSTALAR.bat` | Instalador automático (recomendado) | Clique duas vezes |
| `acervo-install.ps1` | Script PowerShell da instalação | Executado por `INSTALAR.bat` |
| `INSTALE-WINDOWS.md` | Guia completo de instalação | Leia para troubleshooting |
| `build_exe.py` | Compilador do executável `.exe` | `python build_exe.py` |
| `launcher.py` | Launcher para o executável | Gerado por `build_exe.py` |

---

## Quick Start (2 cliques)

1. **Clique duas vezes em `INSTALAR.bat`**
2. Escolha o idioma (1 ou 2)
3. Aguarde a instalação (3-5 minutos)
4. O servidor web abre automaticamente

---

## Compilar um executável `.exe` profissional

Se quiser distribuir um arquivo `.exe` único:

```bash
pip install pyinstaller
python installers/build_exe.py
```

Isso gera: `dist/Acervo-Install.exe`

Agora você pode:
- Enviar o arquivo para usuários finais
- Eles clicam uma vez e tudo instala automaticamente
- Sem necessidade de terminal ou PowerShell

---

## Opções avançadas

### Customizar o caminho de instalação

Editar `INSTALAR.bat` e mudar:
```batch
set INSTALL_PATH=C:\Program Files\Acervo
```

### Mudar idioma padrão

Editar `INSTALAR.bat` e mudar:
```batch
set LANGUAGE=en-US
```

Opções: `pt-BR` (padrão) ou `en-US`

---

## Troubleshooting

### ❌ "Este script não pode ser executado neste sistema"

Abra PowerShell como administrador:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Depois tente novamente.

### ❌ "Python não encontrado"

Instale Python 3.12:
https://www.python.org/downloads/

Marque ✅ "Add Python to PATH" durante a instalação.

### ❌ "Port already in use"

Se a porta 8787 está ocupada, edite:
`C:\Program Files\Acervo\acervo\config.py`

Mude `port: int = 8787` para `port: int = 8788`

---

## Distribuição

### Opção A: Arquivo `.exe` (mais fácil para usuários finais)
```bash
dist/Acervo-Install.exe  (~50-80 MB com Python bundled)
```

### Opção B: Script `.bat` (leve, precisa de Python)
```bash
installers/INSTALAR.bat  (~5 KB)
```

Requer que Python 3.11+ já esteja instalado.

---

## Integração com Windows

O instalador cria automaticamente:
- ✅ Atalho no Desktop (`Acervo.lnk`)
- ✅ Entrada no Menu Iniciar
- ✅ Script de inicialização (`C:\Program Files\Acervo\iniciar.bat`)
- ✅ Ícone personalizado (quando disponível)

---

## Estrutura pós-instalação

Após a instalação em `C:\Program Files\Acervo\`:

```
Acervo/
├── .venv/              ← Ambiente virtual isolado
├── acervo/             ← Código-fonte
├── requirements.txt    ← Dependências
├── README.md
└── iniciar.bat         ← Clique para iniciar o servidor
```

Dados locais do usuário vão para:
```
%APPDATA%\Acervo\acervo.sqlite3
```

---

## Build para macOS/Linux

O script `build_exe.py` é agnóstico, mas para macOS/Linux:

```bash
pip install pyinstaller
python -m PyInstaller --onefile acervo/cli.py --name acervo
```

Gera: `dist/acervo` (executável Unix)

---

Criado em julho de 2026 — Acervo v0.2.0 (Fase 9 MVP)
