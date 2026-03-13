//! PyO3 wrappers for CSAFE response parsing.
//!
//! Exposes `StatusByte`, `CommandResponse`, `Response` as `#[pyclass]`
//! types, plus `parse_status_byte`, `parse_command_responses`, and
//! `parse_response` as `#[pyfunction]`s.

use pyo3::prelude::*;
use pyo3::types::PyBytes;

use crate::response;

// ── StatusByte ───────────────────────────────────────────────────────────

/// Decoded CSAFE response status byte.
#[pyclass(name = "StatusByte")]
#[derive(Clone)]
pub struct PyStatusByte {
    /// Toggles between 0 and 1 on alternate response frames.
    #[pyo3(get)]
    pub frame_toggle: bool,
    /// How the PM processed the previous request frame.
    #[pyo3(get)]
    pub prev_frame_status: String,
    /// Current PM state machine state.
    #[pyo3(get)]
    pub server_state: String,
}

#[pymethods]
impl PyStatusByte {
    fn __repr__(&self) -> String {
        format!(
            "StatusByte(frame_toggle={}, prev_frame_status=\"{}\", server_state=\"{}\")",
            self.frame_toggle, self.prev_frame_status, self.server_state,
        )
    }

    fn __str__(&self) -> String {
        self.__repr__()
    }

    fn __eq__(&self, other: &Self) -> bool {
        self.frame_toggle == other.frame_toggle
            && self.prev_frame_status == other.prev_frame_status
            && self.server_state == other.server_state
    }
}

fn status_byte_to_py(sb: &response::StatusByte) -> PyStatusByte {
    PyStatusByte {
        frame_toggle: sb.frame_toggle,
        prev_frame_status: sb.prev_frame_status.to_string(),
        server_state: sb.server_state.to_string(),
    }
}

// ── CommandResponse ──────────────────────────────────────────────────────

/// A single command response block (command_id + data bytes).
#[pyclass(name = "CommandResponse")]
#[derive(Clone)]
pub struct PyCommandResponse {
    /// Echo of the command ID that generated this response.
    #[pyo3(get)]
    pub command_id: u8,
    inner_data: Vec<u8>,
}

#[pymethods]
impl PyCommandResponse {
    /// Response data bytes.
    #[getter]
    fn data<'py>(&self, py: Python<'py>) -> Bound<'py, PyBytes> {
        PyBytes::new(py, &self.inner_data)
    }

    fn __repr__(&self) -> String {
        format!(
            "CommandResponse(command_id=0x{:02X}, data={:?})",
            self.command_id, self.inner_data,
        )
    }

    fn __str__(&self) -> String {
        self.__repr__()
    }

    fn __eq__(&self, other: &Self) -> bool {
        self.command_id == other.command_id && self.inner_data == other.inner_data
    }
}

fn command_response_to_py(cr: &response::CommandResponse) -> PyCommandResponse {
    PyCommandResponse {
        command_id: cr.command_id,
        inner_data: cr.data.clone(),
    }
}

// ── Response ─────────────────────────────────────────────────────────────

/// A fully parsed CSAFE response (status byte + command response blocks).
#[pyclass(name = "Response")]
#[derive(Clone)]
pub struct PyResponse {
    status_inner: PyStatusByte,
    commands_inner: Vec<PyCommandResponse>,
}

#[pymethods]
impl PyResponse {
    /// Decoded status byte.
    #[getter]
    fn status(&self) -> PyStatusByte {
        self.status_inner.clone()
    }

    /// List of command response blocks.
    #[getter]
    fn commands(&self) -> Vec<PyCommandResponse> {
        self.commands_inner.clone()
    }

    fn __repr__(&self) -> String {
        format!(
            "Response(status={}, commands=[{}])",
            self.status_inner.__repr__(),
            self.commands_inner
                .iter()
                .map(|c| c.__repr__())
                .collect::<Vec<_>>()
                .join(", "),
        )
    }

    fn __str__(&self) -> String {
        self.__repr__()
    }
}

// ── Functions ────────────────────────────────────────────────────────────

/// Parse the CSAFE status byte.
///
/// Returns a ``StatusByte`` with ``frame_toggle``, ``prev_frame_status``,
/// and ``server_state`` fields.
///
/// Raises ``ValueError`` on unknown server state values.
#[pyfunction(name = "parse_status_byte")]
pub fn py_parse_status_byte(byte: u8) -> PyResult<PyStatusByte> {
    let sb = response::parse_status_byte(byte)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    Ok(status_byte_to_py(&sb))
}

/// Parse a sequence of command response blocks from raw bytes.
///
/// Returns a list of ``CommandResponse`` objects.
///
/// Raises ``ValueError`` on truncated or malformed blocks.
#[pyfunction(name = "parse_command_responses")]
pub fn py_parse_command_responses(data: &[u8]) -> PyResult<Vec<PyCommandResponse>> {
    let responses = response::parse_command_responses(data)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    Ok(responses.iter().map(command_response_to_py).collect())
}

/// Parse a complete CSAFE response from frame contents.
///
/// The ``contents`` argument is the raw (unstuffed) payload from frame
/// parsing.  Returns a ``Response`` with ``status`` and ``commands``.
///
/// Raises ``ValueError`` on empty contents, unknown server state, or
/// malformed command response blocks.
#[pyfunction(name = "parse_response")]
pub fn py_parse_response(contents: &[u8]) -> PyResult<PyResponse> {
    let resp = response::parse_response(contents)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    Ok(PyResponse {
        status_inner: status_byte_to_py(&resp.status),
        commands_inner: resp.commands.iter().map(command_response_to_py).collect(),
    })
}

// ── Module registration ──────────────────────────────────────────────────

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyStatusByte>()?;
    m.add_class::<PyCommandResponse>()?;
    m.add_class::<PyResponse>()?;
    m.add_function(wrap_pyfunction!(py_parse_status_byte, m)?)?;
    m.add_function(wrap_pyfunction!(py_parse_command_responses, m)?)?;
    m.add_function(wrap_pyfunction!(py_parse_response, m)?)?;
    Ok(())
}
