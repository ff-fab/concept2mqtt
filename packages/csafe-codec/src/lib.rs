use pyo3::prelude::*;

pub mod commands;
pub mod framing;
mod py_commands;

/// CSAFE protocol codec for Concept2 PM5 rowing monitors.
///
/// This crate provides encoding/decoding for the CSAFE (Communication
/// Specification for Fitness Equipment) protocol used by Concept2 PM5
/// performance monitors over BLE.
#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;

    // Protocol constants
    m.add("EXTENDED_START", framing::EXTENDED_START)?;
    m.add("STANDARD_START", framing::STANDARD_START)?;
    m.add("STOP", framing::STOP)?;
    m.add("STUFF_MARKER", framing::STUFF_MARKER)?;
    m.add("MAX_FRAME_SIZE", framing::MAX_FRAME_SIZE)?;

    // Address constants (extended frames)
    m.add("ADDR_PC_HOST", framing::ADDR_PC_HOST)?;
    m.add("ADDR_DEFAULT_SECONDARY", framing::ADDR_DEFAULT_SECONDARY)?;
    m.add("ADDR_RESERVED", framing::ADDR_RESERVED)?;
    m.add("ADDR_BROADCAST", framing::ADDR_BROADCAST)?;

    // Functions
    m.add_function(wrap_pyfunction!(py_stuff_bytes, m)?)?;
    m.add_function(wrap_pyfunction!(py_unstuff_bytes, m)?)?;
    m.add_function(wrap_pyfunction!(py_compute_checksum, m)?)?;
    m.add_function(wrap_pyfunction!(py_validate_checksum, m)?)?;
    m.add_function(wrap_pyfunction!(py_build_standard_frame, m)?)?;
    m.add_function(wrap_pyfunction!(py_parse_standard_frame, m)?)?;
    m.add_function(wrap_pyfunction!(py_build_extended_frame, m)?)?;
    m.add_function(wrap_pyfunction!(py_parse_extended_frame, m)?)?;
    m.add_function(wrap_pyfunction!(py_parse_frame, m)?)?;

    // Command types and enums
    py_commands::register(m)?;

    Ok(())
}

// ── Python-facing wrappers ──────────────────────────────────────────────

/// Byte-stuff a CSAFE frame payload, escaping reserved bytes 0xF0–0xF3.
#[pyfunction(name = "stuff_bytes")]
fn py_stuff_bytes(data: &[u8]) -> Vec<u8> {
    framing::stuff_bytes(data)
}

/// Reverse byte stuffing on a CSAFE frame payload.
///
/// Raises ``ValueError`` on truncated escape sequences or invalid offsets.
#[pyfunction(name = "unstuff_bytes")]
fn py_unstuff_bytes(data: &[u8]) -> PyResult<Vec<u8>> {
    framing::unstuff_bytes(data).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
}

/// Compute the CSAFE XOR checksum over frame contents.
#[pyfunction(name = "compute_checksum")]
fn py_compute_checksum(data: &[u8]) -> u8 {
    framing::compute_checksum(data)
}

/// Validate a CSAFE checksum against frame contents.
#[pyfunction(name = "validate_checksum")]
fn py_validate_checksum(data: &[u8], expected: u8) -> bool {
    framing::validate_checksum(data, expected)
}

/// Build a standard CSAFE frame from raw contents.
///
/// Raises ``ValueError`` if the resulting frame exceeds the 120-byte limit.
#[pyfunction(name = "build_standard_frame")]
fn py_build_standard_frame(contents: &[u8]) -> PyResult<Vec<u8>> {
    framing::build_standard_frame(contents)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
}

/// Parse a standard CSAFE frame from wire bytes, returning the raw contents.
///
/// Raises ``ValueError`` on missing flags, empty frames, unstuffing errors,
/// or checksum mismatches.
#[pyfunction(name = "parse_standard_frame")]
fn py_parse_standard_frame(frame: &[u8]) -> PyResult<Vec<u8>> {
    framing::parse_standard_frame(frame)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
}

/// Build an extended CSAFE frame with destination and source addresses.
///
/// Raises ``ValueError`` if the resulting frame exceeds the 120-byte limit.
#[pyfunction(name = "build_extended_frame")]
fn py_build_extended_frame(destination: u8, source: u8, contents: &[u8]) -> PyResult<Vec<u8>> {
    framing::build_extended_frame(destination, source, contents)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
}

/// Parse an extended CSAFE frame, returning ``(destination, source, contents)``.
///
/// Raises ``ValueError`` on missing flags, frames too short for the address
/// header, unstuffing errors, or checksum mismatches.
#[pyfunction(name = "parse_extended_frame")]
fn py_parse_extended_frame(frame: &[u8]) -> PyResult<(u8, u8, Vec<u8>)> {
    let ef = framing::parse_extended_frame(frame)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    Ok((ef.destination, ef.source, ef.contents))
}

/// Parse a CSAFE frame, auto-detecting standard vs extended by the start byte.
///
/// Returns a dict with:
/// - ``{"type": "standard", "contents": bytes}`` for standard frames
/// - ``{"type": "extended", "destination": int, "source": int, "contents": bytes}``
///   for extended frames
///
/// Raises ``ValueError`` on parse errors.
#[pyfunction(name = "parse_frame")]
fn py_parse_frame(py: Python<'_>, frame: &[u8]) -> PyResult<PyObject> {
    let result = framing::parse_frame(frame)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    let dict = pyo3::types::PyDict::new(py);
    match result {
        framing::Frame::Standard(contents) => {
            dict.set_item("type", "standard")?;
            dict.set_item("contents", pyo3::types::PyBytes::new(py, &contents))?;
        }
        framing::Frame::Extended(ef) => {
            dict.set_item("type", "extended")?;
            dict.set_item("destination", ef.destination)?;
            dict.set_item("source", ef.source)?;
            dict.set_item("contents", pyo3::types::PyBytes::new(py, &ef.contents))?;
        }
    }
    Ok(dict.into())
}

#[cfg(test)]
mod tests {
    #[test]
    fn version_is_set() {
        assert!(!env!("CARGO_PKG_VERSION").is_empty());
    }
}
