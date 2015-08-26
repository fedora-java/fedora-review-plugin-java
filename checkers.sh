#!/bin/sh
pylint --rcfile pylint.conf fedora-review/java_guidelines.py
pep8 --config pep8.conf fedora-review/java_guidelines.py
