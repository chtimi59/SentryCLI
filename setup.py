from distutils.core import setup

setup(
    entry_points={"console_scripts": ["sentry-cli=sentry.cli:main"]},
)
