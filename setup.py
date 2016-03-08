from setuptools import setup, find_packages

setup(
    name='k8s_drain',
    version='0.1',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'click',
        'blessings',
        'requests'
    ],
    entry_points='''
        [console_scripts]
        k8s_drain=k8s_drain.main:main
    ''',
)
