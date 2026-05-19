mod config;
mod error;
mod server;

use pyo3::prelude::*;

use server::PyMurrServer;

#[pymodule]
fn libmurr(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyMurrServer>()?;
    Ok(())
}
