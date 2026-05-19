use murr::core::MurrError;
use pyo3::exceptions::{PyFileNotFoundError, PyIOError, PyRuntimeError, PyValueError};
use pyo3::prelude::*;

fn raise_named(class: &str, msg: String) -> PyErr {
    Python::try_attach(|py| -> PyErr {
        match py
            .import("murr.client.errors")
            .and_then(|m| m.getattr(class))
            .and_then(|cls| cls.call1((msg.clone(),)))
        {
            Ok(inst) => PyErr::from_value(inst),
            Err(e) => e,
        }
    })
    .unwrap_or_else(|| PyRuntimeError::new_err("could not attach Python GIL"))
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
