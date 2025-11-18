from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="llmchat",
    version="0.1.0",
    author="Your Name",
    description="A simple LLM chatbot using Apple's MLX framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS",
    ],
    python_requires=">=3.8",
    install_requires=[
        "mlx>=0.0.1",
        "mlx-lm>=0.0.1",
        "transformers>=4.30.0",
        "huggingface-hub>=0.16.0",
    ],
    entry_points={
        "console_scripts": [
            "llmchat=llmchat.__main__:main",
        ],
    },
)
