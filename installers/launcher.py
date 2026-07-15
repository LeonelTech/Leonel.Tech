import subprocess
import sys
import os

def main():
    base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(__file__)
    ps_script = os.path.join(base_dir, 'acervo-install.ps1')

    if not os.path.exists(ps_script):
        print('Erro: acervo-install.ps1 não encontrado!')
        input('Pressione ENTER para sair...')
        return 1

    try:
        subprocess.run([
            'powershell',
            '-NoProfile',
            '-ExecutionPolicy', 'Bypass',
            '-File', ps_script,
            '-Language', 'pt-BR'
        ], check=False)
    except Exception as e:
        print(f'Erro ao executar o instalador: {e}')
        input('Pressione ENTER para sair...')
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
