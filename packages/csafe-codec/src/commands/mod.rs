//! CSAFE command types: shared value enums, public commands, and
//! proprietary (Concept2) commands.

pub mod proprietary;
pub mod public;
pub mod types;

// Re-export key types at module level for convenience.
pub use proprietary::*;
pub use public::Command;
pub use types::*;

/// Encode multiple commands into frame contents bytes.
///
/// The returned bytes are suitable for passing to `build_standard_frame()`.
pub fn encode_commands(commands: &[Command]) -> Vec<u8> {
    commands.iter().flat_map(Command::encode).collect()
}

#[cfg(test)]
mod tests;
