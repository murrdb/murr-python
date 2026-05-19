use std::sync::Arc;

use pyo3::prelude::*;
use tokio::sync::oneshot;
use tokio::task::JoinHandle;

use murr::api::MurrHttpService;
use murr::conf::Config;
use murr::service::MurrService;

use crate::config::extract_config;
use crate::error::into_py_err;

struct RunningServer {
    service: Arc<MurrService>,
    shutdown: oneshot::Sender<()>,
    join: JoinHandle<()>,
}

#[pyclass(name = "MurrServer")]
pub struct PyMurrServer {
    state: Option<RunningServer>,
    endpoint: Option<String>,
}

#[pymethods]
impl PyMurrServer {
    #[staticmethod]
    fn _start_blocking(py: Python<'_>, config: &Bound<'_, PyAny>) -> PyResult<Self> {
        let config = extract_config(config)?;
        let runtime = pyo3_async_runtimes::tokio::get_runtime();
        py.detach(|| runtime.block_on(start_inner(config)))
    }

    #[staticmethod]
    fn _start_async<'py>(
        py: Python<'py>,
        config: &Bound<'_, PyAny>,
    ) -> PyResult<Bound<'py, PyAny>> {
        let config = extract_config(config)?;
        pyo3_async_runtimes::tokio::future_into_py(py, async move { start_inner(config).await })
    }

    fn _stop_blocking(&mut self, py: Python<'_>) -> PyResult<()> {
        if let Some(state) = self.state.take() {
            let runtime = pyo3_async_runtimes::tokio::get_runtime();
            py.detach(|| {
                let _ = state.shutdown.send(());
                let _ = runtime.block_on(state.join);
                // dropping `state.service` (the last Arc) closes rocksdb
                drop(state.service);
            });
        }
        self.endpoint = None;
        Ok(())
    }

    fn _stop_async<'py>(&mut self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let taken = self.state.take();
        self.endpoint = None;
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            if let Some(state) = taken {
                let _ = state.shutdown.send(());
                let _ = state.join.await;
                drop(state.service);
            }
            Ok::<(), PyErr>(())
        })
    }

    #[getter]
    fn endpoint(&self) -> Option<String> {
        self.endpoint.clone()
    }

    #[getter]
    fn running(&self) -> bool {
        self.state.is_some()
    }
}

async fn start_inner(config: Config) -> PyResult<PyMurrServer> {
    let service = tokio::task::spawn_blocking(move || MurrService::new(config))
        .await
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("join: {e}")))?
        .map_err(into_py_err)?;
    let service = Arc::new(service);

    let addr = service.config().server.http.addr();
    let router = MurrHttpService::new(service.clone()).router();
    let listener = tokio::net::TcpListener::bind(&addr).await.map_err(|e| {
        pyo3::exceptions::PyIOError::new_err(format!("binding to {addr}: {e}"))
    })?;
    let local_addr = listener
        .local_addr()
        .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("local_addr: {e}")))?;
    let endpoint = format!("http://{local_addr}");

    let (shutdown_tx, shutdown_rx) = oneshot::channel();
    let join = tokio::spawn(async move {
        let _ = axum::serve(listener, router)
            .with_graceful_shutdown(async move {
                let _ = shutdown_rx.await;
            })
            .await;
    });

    Ok(PyMurrServer {
        state: Some(RunningServer {
            service,
            shutdown: shutdown_tx,
            join,
        }),
        endpoint: Some(endpoint),
    })
}
