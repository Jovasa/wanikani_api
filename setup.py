from setuptools import setup, find_packages

setup(
    name='wanikani_api',
    version='0.2.0',
    license="BSD-2-Clause",
    install_requires=[
        "pymongo==4.2.0",
        "urllib3==1.26.12"
    ],
    package_dir={'wanikani_api': 'wanikani_api'},
    packages=["wanikani_api"],
    py_modules=["wanikani_api"]
)
