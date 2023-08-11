from setuptools import setup

setup(
    name="tskit_arg_visualizer",
    version="0.10",
    url='https://github.com/kitchensjn/tskit_arg_visualizer',
    author="James Kitchens",
    author_email="kitchensjn@gmail.com",
    packages=["tskit_arg_visualizer"],
    install_requires=[
        "msprime",
        "IPython",
    ],
    include_package_data=True,
)