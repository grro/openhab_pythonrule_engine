from setuptools import setup
from os import path

PACKAGENAME = 'openhab_pythonrule_engine'
ENTRY_POINT = "pyrule"
DESCRIPTION = "Openhab python rule engine"



this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


setup(
    name=PACKAGENAME,
    packages=[PACKAGENAME],
    version_config={
        "version_format": "{tag}.dev{sha}",
        "starting_version": "0.0.1"
    },
    setup_requires=['better-setuptools-git-version'],
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type='text/markdown',
    license='MIT',
    author='Gregor Roth',
    author_email='gregor.roth@web.de',
    url='https://github.com/grro/openhab_pythonrule_engine',
    entry_points={
        'console_scripts': [
            ENTRY_POINT + '=' + PACKAGENAME + ':main'
        ]
    },
    keywords=[
        'webthings', 'home automation', 'openhab', 'python3', 'python', 'rules'
    ],
    install_requires=[
        'webthing', 'requests', 'sseclient-py>=1.7.2', 'watchdog>=2.1.6', 'pycron>=3.0.0', 'python-dateutil>=2.8.2'
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha"
    ],
)

