from setuptools import setup, find_packages

setup(
    name="RapidRAR",
    version="1.0.0",
    packages=find_packages(),
    py_modules=["main"],
    install_requires=[
        "fastapi",
        "uvicorn",
        "rarfile",
        "rich",
        "numpy",
        "python-multipart",
        # pycuda is optional, usually installed manually or via conda
    ],
    entry_points={
        "console_scripts": [
            "rapidrar=main:main",
        ],
    },
    author="Aoyun",
    description="High-performance RAR password recovery tool",
    python_requires=">=3.8",
)
