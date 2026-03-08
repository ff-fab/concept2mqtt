use pyo3::prelude::*;

pub mod framing;

/// CSAFE protocol codec for Concept2 PM5 rowing monitors.
///
/// This crate provides encoding/decoding for the CSAFE (Communication
/// Specification for Fitness Equipment) protocol used by Concept2 PM5
/// performance monitors over BLE.
#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add_function(wrap_pyfunction!(py_stuff_bytes, m)?)?;
    m.add_function(wrap_pyfunction!(py_unstuff_bytes, m)?)?;
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

#[cfg(test)]
mod tests {
    #[test]
    fn version_is_set() {
        assert!(!env!("CARGO_PKG_VERSION").is_empty());
    }
}
