use pyo3::prelude::*;
use pythonize::depythonize;

use murr::conf::Config;

/// Extract a `murr::conf::Config` from a Python object (typically a dict
/// produced by `Config.model_dump()` on the Python side). Field mapping
/// follows the same serde shape used by the Rust crate's YAML config.
pub fn extract_config(ob: &Bound<'_, PyAny>) -> PyResult<Config> {
    depythonize(ob).map_err(|e| {
        pyo3::exceptions::PyValueError::new_err(format!("invalid config: {e}"))
    })
}
