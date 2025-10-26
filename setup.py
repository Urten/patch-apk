from pathlib import Path
from setuptools import setup, find_packages
import re


HERE = Path(__file__).parent


def read_requirements(req_file: Path):
    if not req_file.exists():
        return []
    lines = req_file.read_text(encoding="utf-8").splitlines()
    reqs = [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]
    return reqs


def get_version(pkg_init: Path):
    if not pkg_init.exists():
        return "0.0.0"
    text = pkg_init.read_text(encoding="utf-8")
    m = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", text)
    return m.group(1) if m else "0.0.0"


long_description = ""
readme_file = HERE / "README.md"
if readme_file.exists():
    long_description = readme_file.read_text(encoding="utf-8")

install_requires = read_requirements(HERE / "requirements.txt")

setup(
    name="patch-apk",
    version=get_version(HERE / "src" / "patch_apk" / "__init__.py"),
    description="App Bundle / Split APK aware patcher for objection",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=install_requires,
    entry_points={
        "console_scripts": [
            "patch-apk=patch_apk.main:main",
        ]
    },
    python_requires=">=3.8",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
