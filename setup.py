from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="retrieval-tool-selector",
    version="0.1.0",
    author="SoulJoy（卓寿杰）",
    author_email="zhuoshoujie@126.com",
    description="Retrieval-augmented tool selector for semantic API matching",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/xiaoyesoso/retrieval-tool-selector",
    packages=find_packages(),
    install_requires=[
        "openai>=1.0.0",
        "numpy>=1.20.0",
        "scikit-learn>=1.0.0"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)