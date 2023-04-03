import io, os
from setuptools import find_packages, setup

def read(path):
    return io.open(os.path.join(os.path.dirname(__file__), path), encoding="utf8").read().strip()

def read_requirements(path):
    return list(map(lambda l: l.strip(), filter(lambda l: not l.startswith(('"', "#", "-", "git+")), read(path).split("\n"))))

setup(
  name="AutoCog",
  version=read("VERSION"),
  description="Automaton & Cognition: programming models for language models",
  url="https://github.com/LLNL/autocog/",
  long_description=read("README.md"),
  long_description_content_type="text/markdown",
  packages=find_packages(exclude=["library", "share", "tests"]),
  install_requires=read_requirements("requirements.txt")
)
