import ast
from pathlib import Path

class ImportRewriter(ast.NodeTransformer):
    """AST Transformer per correggere gli import da app.* a pythia.*"""

    def visit_Import(self, node):
        for alias in node.names:
            if alias.name.startswith('app.'):
                alias.name = alias.name.replace('app.', 'pythia.', 1)
            elif alias.name == 'app':
                alias.name = 'pythia'
        return node

    def visit_ImportFrom(self, node):
        if node.module:
            if node.module.startswith('app.'):
                node.module = node.module.replace('app.', 'pythia.', 1)
            elif node.module == 'app':
                node.module = 'pythia'
        return node

def rewrite_imports_in_file(filepath: Path):
    """Analizza e riscrive gli import in un file Python usando AST."""
    if not filepath.exists() or filepath.suffix != '.py':
        return
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()
    if 'app' not in source:
        return
    try:
        tree = ast.parse(source)
    except SyntaxError:
        print(f'⚠️ Syntax Error in {filepath}, saltato.')
        return
    rewriter = ImportRewriter()
    new_tree = rewriter.visit(tree)
    ast.fix_missing_locations(new_tree)
    new_source = ast.unparse(new_tree)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_source)

def main():
    root = Path.cwd()
    backend_dir = root / 'backend'
    src_pythia = backend_dir / 'src' / 'pythia'
    tests_dir = backend_dir / 'tests'
    print('🔄 Avvio aggiornamento globale degli import (app -> pythia)...')
    if src_pythia.exists():
        for py_file in src_pythia.rglob('*.py'):
            rewrite_imports_in_file(py_file)
    if tests_dir.exists():
        for py_file in tests_dir.rglob('*.py'):
            rewrite_imports_in_file(py_file)
    main_py = backend_dir / 'main.py'
    if main_py.exists():
        rewrite_imports_in_file(main_py)
    for py_file in root.rglob('*.py'):
        if 'venv' in str(py_file) or '.venv' in str(py_file):
            continue
        if py_file.parent == root or py_file.parent == root / 'scripts':
            rewrite_imports_in_file(py_file)
    print('✅ Aggiornamento import completato.')
    dockerfile = backend_dir / 'Dockerfile'
    if dockerfile.exists():
        with open(dockerfile, 'r', encoding='utf-8') as f:
            content = f.read()
        content = content.replace('COPY ./app /app/app', 'COPY ./src /app/src')
        content = content.replace('CMD ["uvicorn", "app.main:app"', 'CMD ["uvicorn", "pythia.api.v1.main:app"')
        content = content.replace('ENV PYTHONPATH=/app', 'ENV PYTHONPATH=/app/src')
        with open(dockerfile, 'w', encoding='utf-8') as f:
            f.write(content)
        print('✅ Dockerfile aggiornato.')
    compose = root / 'docker-compose.yml'
    if compose.exists():
        with open(compose, 'r', encoding='utf-8') as f:
            content = f.read()
        content = content.replace('- ./backend/app:/app/app', '- ./backend/src:/app/src')
        with open(compose, 'w', encoding='utf-8') as f:
            f.write(content)
        print('✅ docker-compose.yml aggiornato.')
if __name__ == '__main__':
    main()