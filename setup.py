from setuptools import setup
import os

setup(
    name = "pykevoplus",
    version = "1.0",
    author = "Carl Seelye",
    author_email = "cseelye@gmail.com",
    description = "Control Kwikset Kevo locks",
    license = "MIT",
    keywords = "kevo kwikset",
    packages = ["pykevoplus"],
    url = "https://github.com/cseelye/pykevoplus",
    long_description = open(os.path.join(os.path.dirname(__file__), "README.rst")).read(),
    install_requires = [
        "requests",
        "beautifulsoup4"
    ]
)
