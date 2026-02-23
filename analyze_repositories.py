"""
Comprehensive Repository Analysis Tool
Analyzes every file in target repositories and extracts patterns
"""
import os
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Set
from collections import defaultdict
import ast
REPOS = {'freqtrade': 'https://github.com/freqtrade/freqtrade', 'hummingbot': 'https://github.com/hummingbot/hummingbot', 'finrl': 'https://github.com/AI4Finance-Foundation/FinRL', 'jesse': 'https://github.com/jesse-ai/jesse', 'qlib': 'https://github.com/microsoft/qlib'}

class RepositoryAnalyzer:

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.analysis = {'files': {}, 'patterns': defaultdict(list), 'metrics': {}, 'dependencies': set(), 'architecture': {}}

    def analyze_all(self):
        """Run complete analysis"""
        print(f'Analyzing {self.repo_path.name}...')
        self.scan_files()
        self.extract_patterns()
        self.analyze_architecture()
        self.extract_dependencies()
        self.calculate_metrics()
        return self.analysis

    def scan_files(self):
        """Scan all Python files"""
        for py_file in self.repo_path.rglob('*.py'):
            if 'test' in str(py_file) or '__pycache__' in str(py_file):
                continue
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.analysis['files'][str(py_file.relative_to(self.repo_path))] = {'lines': len(content.splitlines()), 'size': len(content), 'classes': self._extract_classes(content), 'functions': self._extract_functions(content), 'imports': self._extract_imports(content)}
            except Exception as e:
                print(f'Error reading {py_file}: {e}')

    def _extract_classes(self, content: str) -> List[str]:
        """Extract class names"""
        try:
            tree = ast.parse(content)
            return [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        except:
            return []

    def _extract_functions(self, content: str) -> List[str]:
        """Extract function names"""
        try:
            tree = ast.parse(content)
            return [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        except:
            return []

    def _extract_imports(self, content: str) -> List[str]:
        """Extract import statements"""
        try:
            tree = ast.parse(content)
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend([alias.name for alias in node.names])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
            return imports
        except:
            return []

    def extract_patterns(self):
        """Detect architectural patterns"""
        patterns = {'async': ['async def', 'await ', 'asyncio'], 'event_sourcing': ['EventStore', 'event_log', 'append_event'], 'circuit_breaker': ['CircuitBreaker', 'circuit_breaker'], 'cqrs': ['CommandHandler', 'QueryHandler', 'command_bus'], 'strategy_pattern': ['Strategy', 'IStrategy', 'BaseStrategy'], 'factory_pattern': ['Factory', 'create_', 'builder'], 'observer_pattern': ['Observer', 'subscribe', 'notify'], 'singleton': ['Singleton', '_instance'], 'dependency_injection': ['inject', 'Inject', 'Container'], 'repository_pattern': ['Repository', 'repo'], 'orm': ['SQLAlchemy', 'Model', 'Column'], 'caching': ['cache', 'Cache', 'redis', 'Redis'], 'logging': ['logger', 'logging', 'log_'], 'testing': ['pytest', 'unittest', 'mock'], 'api': ['FastAPI', 'Flask', 'router', 'endpoint'], 'websocket': ['WebSocket', 'ws', 'socket'], 'ml': ['tensorflow', 'torch', 'sklearn', 'model'], 'rl': ['gym', 'agent', 'reward', 'policy']}
        for file_path, file_data in self.analysis['files'].items():
            try:
                with open(self.repo_path / file_path, 'r', encoding='utf-8') as f:
                    content = f.read().lower()
                    for pattern_name, keywords in patterns.items():
                        if any((keyword.lower() in content for keyword in keywords)):
                            self.analysis['patterns'][pattern_name].append(file_path)
            except:
                pass

    def analyze_architecture(self):
        """Analyze overall architecture"""
        dir_counts = defaultdict(int)
        for file_path in self.analysis['files'].keys():
            dir_name = str(Path(file_path).parent)
            dir_counts[dir_name] += 1
        self.analysis['architecture']['directory_structure'] = dict(dir_counts)
        core_modules = []
        for dir_name, count in dir_counts.items():
            if count > 5:
                core_modules.append(dir_name)
        self.analysis['architecture']['core_modules'] = core_modules

    def extract_dependencies(self):
        """Extract all dependencies"""
        all_imports = set()
        for file_data in self.analysis['files'].values():
            all_imports.update(file_data['imports'])
        external = {imp.split('.')[0] for imp in all_imports if not imp.startswith(self.repo_path.name)}
        self.analysis['dependencies'] = sorted(external)

    def calculate_metrics(self):
        """Calculate code metrics"""
        total_lines = sum((f['lines'] for f in self.analysis['files'].values()))
        total_classes = sum((len(f['classes']) for f in self.analysis['files'].values()))
        total_functions = sum((len(f['functions']) for f in self.analysis['files'].values()))
        self.analysis['metrics'] = {'total_files': len(self.analysis['files']), 'total_lines': total_lines, 'total_classes': total_classes, 'total_functions': total_functions, 'avg_lines_per_file': total_lines / len(self.analysis['files']) if self.analysis['files'] else 0, 'avg_functions_per_file': total_functions / len(self.analysis['files']) if self.analysis['files'] else 0}

def clone_repositories(target_dir: str='./repos'):
    """Clone all target repositories"""
    os.makedirs(target_dir, exist_ok=True)
    for name, url in REPOS.items():
        repo_path = os.path.join(target_dir, name)
        if not os.path.exists(repo_path):
            print(f'Cloning {name}...')
            subprocess.run(['git', 'clone', '--depth', '1', url, repo_path])
        else:
            print(f'{name} already cloned')

def analyze_all_repos(repos_dir: str='./repos'):
    """Analyze all repositories"""
    results = {}
    for name in REPOS.keys():
        repo_path = os.path.join(repos_dir, name)
        if os.path.exists(repo_path):
            analyzer = RepositoryAnalyzer(repo_path)
            results[name] = analyzer.analyze_all()
    return results

def generate_comparison_report(results: Dict):
    """Generate comparative analysis report"""
    report = []
    report.append('# COMPREHENSIVE REPOSITORY ANALYSIS REPORT\n')
    report.append(f'**Repositories Analyzed**: {len(results)}\n')
    report.append(f"**Analysis Date**: {__import__('datetime').datetime.now()}\n\n")
    report.append('## Code Metrics Comparison\n\n')
    report.append('| Repository | Files | Lines | Classes | Functions | Avg Lines/File |\n')
    report.append('|------------|-------|-------|---------|-----------|----------------|\n')
    for name, data in results.items():
        m = data['metrics']
        report.append(f"| {name} | {m['total_files']} | {m['total_lines']:,} | {m['total_classes']} | {m['total_functions']} | {m['avg_lines_per_file']:.1f} |\n")
    report.append('\n## Pattern Adoption Matrix\n\n')
    all_patterns = set()
    for data in results.values():
        all_patterns.update(data['patterns'].keys())
    report.append('| Pattern | ' + ' | '.join(results.keys()) + ' |\n')
    report.append('|---------|' + '|'.join(['-------'] * len(results)) + '|\n')
    for pattern in sorted(all_patterns):
        row = f'| {pattern} |'
        for name in results.keys():
            count = len(results[name]['patterns'].get(pattern, []))
            status = '✅' if count > 0 else '❌'
            row += f' {status} ({count}) |'
        report.append(row + '\n')
    report.append('\n## Common Dependencies\n\n')
    all_deps = defaultdict(list)
    for name, data in results.items():
        for dep in data['dependencies']:
            all_deps[dep].append(name)
    common_deps = {dep: repos for dep, repos in all_deps.items() if len(repos) >= 3}
    for dep, repos in sorted(common_deps.items()):
        report.append(f"- **{dep}**: {', '.join(repos)}\n")
    report.append('\n## Architecture Insights\n\n')
    for name, data in results.items():
        report.append(f'### {name}\n')
        report.append(f"**Core Modules**: {', '.join(data['architecture']['core_modules'][:5])}\n\n")
    return ''.join(report)

def extract_implementation_patterns(results: Dict):
    """Extract specific implementation patterns"""
    patterns = {}
    for name, data in results.items():
        patterns[name] = {'has_async': len(data['patterns'].get('async', [])) > 0, 'has_event_sourcing': len(data['patterns'].get('event_sourcing', [])) > 0, 'has_cqrs': len(data['patterns'].get('cqrs', [])) > 0, 'has_circuit_breaker': len(data['patterns'].get('circuit_breaker', [])) > 0, 'has_caching': len(data['patterns'].get('caching', [])) > 0, 'has_websocket': len(data['patterns'].get('websocket', [])) > 0, 'has_ml': len(data['patterns'].get('ml', [])) > 0, 'has_rl': len(data['patterns'].get('rl', [])) > 0, 'strategy_files': data['patterns'].get('strategy_pattern', []), 'api_files': data['patterns'].get('api', []), 'orm_files': data['patterns'].get('orm', [])}
    return patterns

def main():
    """Main execution"""
    print('=' * 80)
    print('COMPREHENSIVE REPOSITORY ANALYSIS')
    print('=' * 80)
    print('\n[1/4] Cloning repositories...')
    clone_repositories()
    print('\n[2/4] Analyzing repositories...')
    results = analyze_all_repos()
    print('\n[3/4] Generating comparison report...')
    report = generate_comparison_report(results)
    with open('REPOSITORY_ANALYSIS_REPORT.md', 'w') as f:
        f.write(report)
    print('\n[4/4] Extracting implementation patterns...')
    patterns = extract_implementation_patterns(results)
    with open('repository_analysis.json', 'w') as f:
        json.dump({'results': results, 'patterns': patterns}, f, indent=2, default=str)
    print('\n' + '=' * 80)
    print('ANALYSIS COMPLETE')
    print('=' * 80)
    print(f'\nReports generated:')
    print('  - REPOSITORY_ANALYSIS_REPORT.md')
    print('  - repository_analysis.json')
    print(f"\nTotal files analyzed: {sum((r['metrics']['total_files'] for r in results.values()))}")
    print(f"Total lines of code: {sum((r['metrics']['total_lines'] for r in results.values())):,}")
if __name__ == '__main__':
    main()