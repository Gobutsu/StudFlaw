from setuptools import setup, find_packages

requirements = [x.strip() for x in open("requirements.txt", "r").readlines()]

setup(
    name='StudFlaw',
    version='0.1.1',
    description='Search people using their french diploma records',
    author='Gobutsu',
    packages=find_packages(),  # Automatically find packages in your directory
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'studflaw = studflaw.main:main'
        ]
    },
    python_requires='>=3.6',
)
