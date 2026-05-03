"""Dataset registry — discovers and tracks installed dataset plugins.

Walks govlink.datasets at startup, imports each subpackage's
dataset.py registration module, and exposes the resulting catalogue
to the API and CLI layers.
"""

# TODO(phase-4): Implement DatasetRegistry and discovery logic.
