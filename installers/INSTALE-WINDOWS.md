# Acervo — Guia de Instalação para Windows

## Método 1: Instalador Automático (Recomendado) ⭐

### Passo 1: Baixar os arquivos
1. Vá ao repositório: https://github.com/leoneltech/leonel.tech
2. Clique em **Code** → **Download ZIP**
3. Extraia em uma pasta (ex: `C:\Users\seu_usuario\Downloads\Leonel.Tech`)

### Passo 2: Executar o instalador
1. Abra a pasta onde extraiu os arquivos
2. Navegue até: `installers\`
3. **Clique duas vezes em `INSTALAR.bat`**
4. Escolha o idioma (1 para Português, 2 para English)

### O que o instalador faz automaticamente:
- ✅ Verifica se Python 3.11+ está instalado
- ✅ Cria um ambiente virtual isolado
- ✅ Instala todas as dependências (SQLAlchemy, FastAPI, Pydantic…)
- ✅ Cria um atalho no Desktop
- ✅ Cria um script de inicialização (`iniciar.bat`)
- ✅ Inicia o servidor automaticamente

### Passo 3: Pronto!
O servidor web será aberto automaticamente em:
```
http://127.0.0.1:8787
```

Agora você pode:
- 📂 Selecionar sua pasta de origem (documentos do cliente)
- 📁 Selecionar a pasta de destino (repositório)
- ▶️ Clicar em "Iniciar sessão" para começar a catalogação

---

## Método 2: Instalação Manual via PowerShell

Se o instalador não funcionar, execute manualmente:

### Passo 1: Abrir PowerShell como Administrador
1. Clique em **Iniciar**
2. Digite: `powershell`
3. Clique com botão direito em **Windows PowerShell**
4. Clique em **Executar como administrador**

### Passo 2: Navegar até a pasta do projeto
```powershell
cd C:\caminho\para\Leonel.Tech
```

### Passo 3: Executar o instalador
```powershell
powershell -ExecutionPolicy Bypass -File "installers\acervo-install.ps1" -Language "pt-BR"
```

---

## Método 3: Instalação Manual (Python já instalado)

Se você prefere fazer tudo manualmente:

### Passo 1: Verificar Python
```powershell
python --version
```
Deve mostrar Python 3.11 ou superior. Se não tiver, baixe em:
https://www.python.org/downloads/

### Passo 2: Criar ambiente virtual
```powershell
python -m venv .venv
.venv\Scripts\activate
```

### Passo 3: Instalar dependências
```powershell
pip install -r requirements.txt
```

### Passo 4: Executar os testes
```powershell
python -m pytest
```
Deve mostrar: `25 passed`

### Passo 5: Iniciar o servidor
```powershell
python -m acervo.cli serve
```

Abra no navegador:
```
http://127.0.0.1:8787
```

---

## Usando a linha de comando (avançado)

Para executar uma sessão de preservação sem a interface web:

```powershell
python -m acervo.cli preserve ^
  --collection "Caso Silva" ^
  --source "C:\Users\seu_usuario\Documents\cliente_arquivos" ^
  --destination "C:\repository"
```

---

## Solução de Problemas

### ❌ Erro: "Python não encontrado"
**Solução:** Instale Python 3.12 de https://www.python.org/downloads/

### ❌ Erro: "Este script não pode ser executado neste sistema"
**Solução:** Abra PowerShell como administrador e execute:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### ❌ Erro: "ModuleNotFoundError: No module named 'acervo'"
**Solução:** Verifique se está dentro do diretório `Leonel.Tech` e se o ambiente virtual está ativado (deve ver `(.venv)` no prompt)

### ❌ Porta 8787 já está em uso
**Solução:** A porta pode estar em uso por outro programa. Abra outra aba do navegador em:
```
http://127.0.0.1:8787
```

Se não funcionar, mude para outra porta (edite `acervo/config.py` e altere `port: int = 8787` para `port: int = 8788`)

---

## Atualizar a instalação

Se já tem Acervo instalado e quer atualizar:

```powershell
cd "C:\Program Files\Acervo"
.venv\Scripts\activate
pip install --upgrade -r requirements.txt
```

---

## Próximos Passos

1. ✅ Executar um teste de preservação (veja na interface web)
2. 📖 Ler a documentação em `docs/ARCHITECTURE.md`
3. 🧪 Explorar os testes em `tests/`
4. 💬 Contribuir no GitHub: https://github.com/leoneltech/leonel.tech

---

**Criado em julho de 2026 — Acervo v0.2.0**
