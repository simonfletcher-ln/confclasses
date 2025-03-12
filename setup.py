from setuptools import setup, find_packages

setup(
    name='confclasses',
    version='0.1.0',
    py_modules=['confclasses'],
    author='Simon Fletcher',
    author_email='simon.fletcher@lexisnexisrisk.com',
    description='A simple wrapper around dataclasses, for general configuration',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/yourusername/confclasses',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6'
)