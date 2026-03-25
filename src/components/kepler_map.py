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


_FULLWIDTH_SCRIPT = """
<script>
(function() {
    try {
        var frame = window.frameElement;
        if (!frame) return;
        frame.style.width = '100%';
        // Find only the element-container wrapper (1-3 levels up) and expand it
        var el = frame.parentElement;
        for (var i = 0; i < 4 && el; i++) {
            var isEC = (el.classList && el.classList.contains('element-container')) ||
                       (el.dataset && el.dataset.testid === 'element-container');
            if (isEC) {
                el.style.width = '100vw';
                el.style.maxWidth = '100vw';
                el.style.marginLeft = 'calc(-50vw + 50%)';
                break;
            }
            el = el.parentElement;
        }
    } catch(e) {}
})();
</script>
"""


def kepler_static(
    data: dict[str, pd.DataFrame],
    config: dict,
    height: int = 650,
    read_only: bool = True,
    center_map: bool = False,
    full_width: bool = False,
) -> None:
    """Render a Kepler.gl map in Streamlit.

    Parameters
    ----------
    data : dict mapping dataset name -> DataFrame
    config : kepler.gl config dict (with version and config keys)
    height : map height in pixels
    read_only : hide side panel
    center_map : auto-fit bounds to data
    full_width : expand map to full viewport width
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

    fullwidth_inject = _FULLWIDTH_SCRIPT if full_width else ""

    injected = (
        template[:k]
        + '<body><script>window.__keplerglDataConfig = '
        + kepler_data
        + ";</script>"
        + fullwidth_inject
        + template[k + 6:]
    )

    components.html(injected, height=height + 10)
