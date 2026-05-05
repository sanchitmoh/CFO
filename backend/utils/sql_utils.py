"""
AI CFO — SQL Utilities

SEC-CRIT-002: Escape SQL LIKE/ILIKE wildcard characters to prevent
pattern injection attacks (CPU exhaustion via crafted wildcards).
"""


def escape_like(value: str) -> str:
    """Escape SQL LIKE/ILIKE wildcard characters.

    Prevents attackers from injecting ``%`` or ``_`` wildcards into
    user-supplied search terms, which could force expensive full-table
    scans or manipulate pattern matching.

    The backslash is escaped first to avoid double-escaping.

    Usage::

        from utils.sql_utils import escape_like

        filters.append(
            Transaction.description.ilike(f"%{escape_like(search)}%")
        )
    """
    return (
        value
        .replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )
