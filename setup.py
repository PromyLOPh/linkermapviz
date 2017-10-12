from distutils.core import setup

setup(
    name='linkermapviz',
    version='0.1.0',
    author='Lars-Dominik Braun',
    author_email='lars+linkermapviz@6xq.net',
    packages=['linkermapviz'],
    license='LICENSE.txt',
    description='Visualize GNU ld’s linker map with a tree map.',
    install_requires=[
        'bokeh',
        'squarify',
    ],
    entry_points={
    'console_scripts': [
            'linkermapviz = linkermapviz:main',
            ],
    },
)

