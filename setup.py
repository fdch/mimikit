#################### Maintained by Hatch ####################
# This file is auto-generated by hatch. If you'd like to customize this file
# please add your changes near the bottom marked for 'USER OVERRIDES'.
# EVERYTHING ELSE WILL BE OVERWRITTEN by hatch.
#############################################################
from io import open

from setuptools import setup, find_packages

with open('mmk/__init__.py', 'r') as f:
    for line in f:
        if line.startswith('__version__'):
            version = line.strip().split('=')[1].strip(' \'"')
            break
    else:
        version = '0.0.1'

with open('README.md', 'r', encoding='utf-8') as f:
    readme = f.read()

import os

with open(os.path.join(os.path.dirname(__file__), 'requirements.txt'), "r", encoding="utf-8") as f:
    REQUIRES = [ln.strip() for ln in f.readlines() if ln.strip()]

PACKAGES = find_packages(exclude=('tests', 'tests.*'))
print(PACKAGES)

kwargs = {
    'name': 'mmk',
    'version': version,
    'description': 'Python module for generating audio with neural networks',
    'long_description': readme,
    "long_description_content_type": "text/markdown",
    'author': 'k-tonal',
    'author_email': 'ktonalberlin@gmail.com',
    'maintainer': 'Antoine Daurat',
    'maintainer_email': 'antoinedaurat@gmail.com',
    'url': 'https://github.com/k-tonal/mmk',
    'download_url': 'https://github.com/k-tonal/mmk',
    # 'license': 'GNU General Public License v3 (GPLv3)',
    'classifiers': [
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        "Intended Audience :: Science/Research",
        "Intended Audience :: Other Audience",
        "Topic :: Multimedia :: Sound/Audio :: Analysis",
        "Topic :: Multimedia :: Sound/Audio :: Sound Synthesis",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    "keywords": "audio music sound deep-learning",
    'python_requires': '>=3.6',
    'install_requires': REQUIRES,
    'tests_require': ['coverage', 'pytest'],
    'packages': PACKAGES,
    "entry_points": {
        'console_scripts': [
            'freqnet-db=mmk.data.freqnet_db:main'
        ]}

}

#################### BEGIN USER OVERRIDES ####################
# Add your customizations in this section.
# kwargs["long_description_content_type"] = "text/markdown"
# kwargs['author'] = 'k-tonal'
# kwargs['author_email'] = 'ktonalberlin@gmail.com'
# kwargs['maintainer'] = 'Antoine Daurat'
# kwargs['maintainer_email'] = 'antoinedaurat@gmail.com'
# kwargs['url'] = 'https://github.com/k-tonal/mmk'
# kwargs['license'] = 'GNU General Public License v3 (GPLv3)'

###################### END USER OVERRIDES ####################

setup(**kwargs)
