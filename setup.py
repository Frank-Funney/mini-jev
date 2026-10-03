[metadata]
name = mini-jev
version = 1.0.0
author = MiniJEV Team
author_email = mini-jev@example.com
description = 超轻量级结构化决策引擎，为老机器设计的JEV替代方案
long_description = file: README.md
long_description_content_type = text/markdown
url = https://github.com/your-org/mini-jev
license = MIT
classifiers =
    Development Status :: 4 - Beta
    Intended Audience :: Developers
    License :: OSI Approved :: MIT License
    Programming Language :: Python :: 3
    Programming Language :: Python :: 3.10
    Programming Language :: Python :: 3.11
    Programming Language :: Python :: 3.12
    Topic :: Software Development :: Libraries :: Python Modules

[options]
packages = find:
python_requires = >=3.10
install_requires =

[options.packages.find]
where = .
exclude =
    tests*
    *test*

[options.entry_points]
console_scripts =
    mini-jev = mini_jev.cli:main
