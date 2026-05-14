"""Shared schema types used by automation services."""
from enum import Enum


class Environment(str, Enum):
    SANDBOX = "SANDBOX"
    PRODUCTION = "PRODUCTION"
