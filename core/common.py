#!/usr/bin/python3
"""
Non-module specific items useful to all components.
"""


def enum(**enums):
    """Create enum-type object. Create as: Numbers=enum(ONE=1, TWO=2)"""
    return type('Enum', (), enums)


