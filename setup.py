from setuptools import setup


def readme():
    with open("README.md") as f:
        return f.read()


setup(
    name="slurminade",
    version="0.5.4",
    description="A decorator-based slurm runner",
    long_description=readme(),
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
    ],
    keywords="slurm",
    url="https://github.com/d-krupke/slurminade",
    author="Dominik Krupke",
    author_email="krupke@ibr.cs.tu-bs.de",
    license="MIT",
    packages=["slurminade"],
    install_requires=["simple_slurm"],
    entry_points={
        #  'console_scripts': ['slurminade-exec=slurminade.execute:main'],
    },
    python_requires=">=3.7",
    include_package_data=True,
    zip_safe=False,
)
