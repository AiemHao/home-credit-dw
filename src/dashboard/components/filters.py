"""Shared sidebar filters (cross-filtering state).

Filter values live in st.session_state under "_persist_<dim>" so they survive page switches, and
charts can set them (click a bar -> filter) through set_filter().
"""
from __future__ import annotations

from dataclasses import dataclass, field

import streamlit as st

from queries import DIMENSIONS, distinct_values

SIDEBAR_DIMS = ["age_bucket", "income_bracket", "income_type", "gender", "contract_type", "education_type"]


def _persist_key(dim: str) -> str:
    return f"_persist_{dim}"


def _widget_key(dim: str) -> str:
    return f"filter_{dim}"


@dataclass(frozen=True)
class Filters:
    values: dict[str, tuple[str, ...]] = field(default_factory=dict)

    def where(self, **extra: str) -> tuple[str, tuple]:
        """SQL WHERE clause + params. extra=dim=value adds equality conditions (drill path)."""
        clauses, params = [], []
        for dim, vals in self.values.items():
            if vals:
                clauses.append(f"{dim} IN ({', '.join('?' for _ in vals)})")
                params.extend(vals)
        for dim, val in extra.items():
            if dim not in DIMENSIONS:
                raise ValueError(dim)
            clauses.append(f"{dim} = ?")
            params.append(val)
        return ("WHERE " + " AND ".join(clauses) if clauses else ""), tuple(params)

    @property
    def active(self) -> bool:
        return any(self.values.values())


def set_filter(dim: str, values: list[str]) -> None:
    """Programmatic filter change (used by click-to-filter charts). Caller should st.rerun()."""
    st.session_state[_persist_key(dim)] = list(values)


def _sync(dim: str) -> None:
    """Widget changed by the user -> copy into the persistent key (runs before the rerun)."""
    st.session_state[_persist_key(dim)] = list(st.session_state[_widget_key(dim)])


def _clear_all() -> None:
    for dim in SIDEBAR_DIMS:
        set_filter(dim, [])


def sidebar_filters() -> Filters:
    # Streamlit drops widget state when the page changes, so the source of truth is the
    # non-widget "_persist_<dim>" key; widgets are re-seeded from it on every run.
    st.sidebar.header("Filters")
    st.sidebar.caption("Apply to every page. Click a bar on a chart to filter by it.")
    chosen: dict[str, tuple[str, ...]] = {}
    for dim in SIDEBAR_DIMS:
        options = distinct_values(dim)
        values = [v for v in st.session_state.get(_persist_key(dim), []) if v in options]
        st.session_state[_widget_key(dim)] = values
        st.sidebar.multiselect(DIMENSIONS[dim], options, key=_widget_key(dim), on_change=_sync, args=(dim,))
        chosen[dim] = tuple(values)
    st.sidebar.button("Clear all filters", width="stretch", on_click=_clear_all)
    return Filters(chosen)
