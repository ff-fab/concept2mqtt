use pyo3::prelude::*;

/// CSAFE protocol codec for Concept2 PM5 rowing monitors.
///
/// This crate provides encoding/decoding for the CSAFE (Communication
/// Specification for Fitness Equipment) protocol used by Concept2 PM5
/// performance monitors over BLE.
#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}

#[cfg(test)]
mod tests {
    #[test]
    fn version_is_set() {
        assert!(!env!("CARGO_PKG_VERSION").is_empty());
    }
}
