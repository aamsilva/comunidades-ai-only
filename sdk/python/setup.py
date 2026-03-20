from setuptools import setup, find_packages

setup(
    name="a2a-protocol",
    version="0.1.0",
    description="A2A Protocol SDK - AI-to-AI Communication",
    long_description=open("../../README.md").read(),
    long_description_content_type="text/markdown",
    author="Hexa Labs",
    author_email="dev@hexalabs.io",
    url="https://github.com/aamsilva/comunidades-ai-only",
    packages=find_packages(),
    install_requires=[
        "pynacl>=1.5.0",
        "msgpack>=1.0.0",
        "websockets>=12.0",
        "aiohttp>=3.9.0",
    ],
    python_requires=">=3.9",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="ai agents protocol communication a2a",
)
