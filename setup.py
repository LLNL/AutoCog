import io, os, glob
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
  packages=find_packages(exclude=["share", "tests"]),
  install_requires=read_requirements("requirements.txt"),
  data_files=[
      ( 'share/autocog/library/mcq',        glob.glob("share/library/mcq/*") ),
      ( 'share/autocog/library/dfl',        glob.glob("share/library/dfl/*") ),
      ( 'share/autocog/library/elementary', glob.glob("share/library/elementary/*") ),
      ( 'share/autocog/library/tools',      glob.glob("share/library/tools/*") )
  ],
)
