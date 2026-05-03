"""Dataset registry root.

Each subdirectory under this package represents a single dataset
and must contain:
    - dataset.py  (registration metadata)
    - model.py    (SQLAlchemy + Pydantic schemas)
    - parser.py   (BaseParser implementation)
    - source.py   (BaseSource implementation)

Datasets are auto-discovered at startup by govlink.core.registry.
"""
