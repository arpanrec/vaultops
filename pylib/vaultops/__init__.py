#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module provides functions for initializing and interacting with HashiCorp Vault.
"""


class VaultOpsRetryError(Exception):
    """
    Exception raised when the init_unseal process is to be tried.
    """

    def __init__(self, *args, **kwargs):  # real signature unknown
        super().__init__(args, kwargs)


class VaultOpsSafeExit(Exception):
    """
    Exit the program safely.
    """

    def __init__(self, *args, **kwargs):  # real signature unknown
        super().__init__(args, kwargs)
