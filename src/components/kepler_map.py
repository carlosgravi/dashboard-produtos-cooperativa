"""Lightweight Kepler.gl renderer for Streamlit.

Replaces the full keplergl + streamlit-keplergl packages (which have heavy
Jupyter/pyarrow dependencies) with a minimal shim that does the same thing:
load the bundled keplergl.html template, inject data + config as JSON, and
render via st.components.v1.html().

Only supports plain pandas DataFrames (not GeoDataFrames or Arrow).
"""

import json
from pathlib import Path

import pandas as pd
import streamlit.components.v1 as components

_TEMPLATE_PATH = Path(__file__).parent.parent / "static" / "keplergl.html"
_TEMPLATE_CACHE: str | None = None


def _load_template() -> str:
    global _TEMPLATE_CACHE
    if _TEMPLATE_CACHE is None:
        _TEMPLATE_CACHE = _TEMPLATE_PATH.read_text(encoding="utf-8")
    return _TEMPLATE_CACHE


def _df_to_dict(df: pd.DataFrame) -> dict:
    """Convert DataFrame to kepler.gl dict format (same as keplergl._df_to_dict)."""
    df_copy = df.copy()
    for col in df_copy.columns:
        try:
            if len(df_copy) > 0:
                json.dumps(df_copy[col].iloc[0])
        except (TypeError, OverflowError):
            df_copy[col] = df_copy[col].astype(str)
    return df_copy.to_dict("split")


def kepler_static(
    data: dict[str, pd.DataFrame],
    config: dict,
    height: int = 650,
    read_only: bool = True,
    center_map: bool = False,
) -> None:
    """Render a Kepler.gl map in Streamlit.

    Parameters
    ----------
    data : dict mapping dataset name -> DataFrame
    config : kepler.gl config dict (with version and config keys)
    height : map height in pixels
    read_only : hide side panel
    center_map : auto-fit bounds to data
    """
    template = _load_template()
    k = template.find("<body>")

    # Serialize datasets
    datasets = {}
    for name, df in data.items():
        datasets[name] = _df_to_dict(df)

    kepler_data = json.dumps({
        "config": config.get("config", config),
        "data": datasets,
        "options": {"readOnly": read_only, "centerMap": center_map},
    })

    resize_js = "try{window.frameElement.style.setProperty('width','100%','important')}catch(e){}"

    injected = (
        template[:k]
        + "<body><script>window.__keplerglDataConfig = "
        + kepler_data
        + ";" + resize_js
        + ";</script>"
        + template[k + 6:]
    )

    components.html(injected, height=height + 10, scrolling=False)
