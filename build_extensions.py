import os
import sys
from setuptools import setup, Extension
from Cython.Build import cythonize
import subprocess

def build_cython_extensions():
    temp_repos_path = os.path.join(os.path.dirname(__file__), 'temp_repos')
    extensions = []
    for root, dirs, files in os.walk(temp_repos_path):
        print(f'Scanning path: {root}')
        for file in files:
            if file.endswith('.pyx'):
                pyx_path = os.path.join(root, file)
                module_name = os.path.relpath(pyx_path, temp_repos_path).replace(os.sep, '.').replace('.pyx', '')
                ext = Extension(module_name, [pyx_path])
                extensions.append(ext)
    if extensions:
        setup(ext_modules=cythonize(extensions, language_level='3'), script_args=['build_ext', '--inplace'])
        print('Cython extensions compiled successfully.')
    else:
        print('No .pyx files found in temp_repos.')
if __name__ == '__main__':
    build_cython_extensions()