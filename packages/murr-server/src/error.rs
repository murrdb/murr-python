use murr::core::MurrError;
use pyo3::exceptions::{PyFileNotFoundError, PyIOError, PyRuntimeError, PyValueError};
use pyo3::prelude::*;

fn raise_named(class: &str, msg: String) -> PyErr {
    let result: PyResult<PyErr> = Python::try_attach(|py| {
        let module = py.import("murr.client.errors")?;
        let cls = module.getattr(class)?;
        let inst = cls.call1((msg,))?;
        Ok::<PyErr, PyErr>(PyErr::from_value(inst))
    })
    .unwrap_or_else(|_| Ok(PyRuntimeError::new_err("could not attach GIL")));
    match result {
        Ok(e) => e,
        Err(e) => e,
    }
}

pub fn into_py_err(err: MurrError) -> PyErr {
    match err {
        MurrError::TableNotFound(name) => {
            PyFileNotFoundError::new_err(format!("table not found: {name}"))
        }
        MurrError::TableAlreadyExists(name) => {
            PyValueError::new_err(format!("table already exists: {name}"))
        }
        MurrError::ConfigParsingError(msg) => PyValueError::new_err(msg),
        MurrError::IoError(msg) => PyIOError::new_err(msg),
        MurrError::ArrowError(msg) => PyRuntimeError::new_err(format!("arrow error: {msg}")),
        MurrError::TableError(msg) => raise_named("MurrTableError", format!("table error: {msg}")),
        MurrError::SegmentError(msg) => {
            raise_named("MurrSegmentError", format!("segment error: {msg}"))
        }
    }
}
