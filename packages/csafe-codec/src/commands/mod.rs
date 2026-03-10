//! CSAFE command types: shared value enums, public commands, and
//! proprietary (Concept2) commands.

pub mod proprietary;
pub mod public;
pub mod types;

use crate::framing::FrameBuf;

// Re-export key types at module level for convenience.
pub use proprietary::*;
pub use public::Command;
pub use types::*;

pub fn encode_commands_into(commands: &[Command], buf: &mut FrameBuf) {
    for cmd in commands {
        cmd.encode_into(buf);
    }
}

/// Encode multiple commands into frame contents bytes.
///
/// The returned bytes are suitable for passing to `build_standard_frame()`.
pub fn encode_commands(commands: &[Command]) -> Vec<u8> {
    let mut buf = FrameBuf::new();
    encode_commands_into(commands, &mut buf);
    buf.into_vec()
}

#[cfg(test)]
mod tests;
