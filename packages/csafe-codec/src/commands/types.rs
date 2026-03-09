use std::fmt;

/// Errors related to command type conversions.
#[derive(Debug, Clone, PartialEq, Eq)]
#[non_exhaustive]
pub enum CommandError {
    /// A raw byte value does not correspond to any known enum variant.
    InvalidEnumValue {
        /// Name of the enum type.
        type_name: &'static str,
        /// The invalid raw value.
        value: u8,
    },
}

impl fmt::Display for CommandError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidEnumValue { type_name, value } => {
                write!(f, "invalid {type_name} value: 0x{value:02X}")
            }
        }
    }
}

impl std::error::Error for CommandError {}

// ---------------------------------------------------------------------------
// Macro to reduce boilerplate: derives, repr, non_exhaustive, Display,
// and TryFrom<u8> for each enum.
// ---------------------------------------------------------------------------

macro_rules! csafe_enum {
    (
        $(#[$meta:meta])*
        $name:ident {
            $( $(#[$vmeta:meta])* $variant:ident = $val:expr ),+ $(,)?
        }
    ) => {
        $(#[$meta])*
        #[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
        #[repr(u8)]
        #[non_exhaustive]
        pub enum $name {
            $( $(#[$vmeta])* $variant = $val ),+
        }

        impl fmt::Display for $name {
            fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
                fmt::Debug::fmt(self, f)
            }
        }

        impl TryFrom<u8> for $name {
            type Error = CommandError;
            fn try_from(value: u8) -> Result<Self, Self::Error> {
                match value {
                    $( $val => Ok(Self::$variant), )+
                    _ => Err(CommandError::InvalidEnumValue {
                        type_name: stringify!($name),
                        value,
                    }),
                }
            }
        }
    };
}

// ---------------------------------------------------------------------------
// Enum definitions – sourced from docs/planning/spec/csafe/enums.yaml
// ---------------------------------------------------------------------------

csafe_enum! {
    /// Type of workout programmed on the erg.
    WorkoutType {
        /// Free row, no splits.
        JustRowNoSplits = 0,
        /// Free row with splits.
        JustRowSplits = 1,
        /// Fixed distance, no splits.
        FixedDistNoSplits = 2,
        /// Fixed distance with splits.
        FixedDistSplits = 3,
        /// Fixed time, no splits.
        FixedTimeNoSplits = 4,
        /// Fixed time with splits.
        FixedTimeSplits = 5,
        /// Fixed time interval.
        FixedTimeInterval = 6,
        /// Fixed distance interval.
        FixedDistInterval = 7,
        /// Variable interval.
        VariableInterval = 8,
        /// Variable interval with undefined rest.
        VariableUndefinedRestInterval = 9,
        /// Fixed calorie with splits.
        FixedCalorieSplits = 10,
        /// Fixed watt-minute with splits.
        FixedWattMinuteSplits = 11,
        /// Fixed calorie interval.
        FixedCalorieInterval = 12,
    }
}

csafe_enum! {
    /// Type of the current interval.
    IntervalType {
        /// Time interval.
        Time = 0,
        /// Distance interval.
        Dist = 1,
        /// Rest interval.
        Rest = 2,
        /// Time with undefined rest.
        TimeRestUndefined = 3,
        /// Distance with undefined rest.
        DistRestUndefined = 4,
        /// Undefined rest.
        RestUndefined = 5,
        /// Calorie interval.
        Calorie = 6,
        /// Calorie with undefined rest.
        CalorieRestUndefined = 7,
        /// Watt-minute interval.
        WattMinute = 8,
        /// Watt-minute with undefined rest.
        WattMinuteRestUndefined = 9,
        /// No interval.
        None = 255,
    }
}

csafe_enum! {
    /// Current state of the workout state machine.
    WorkoutState {
        /// Waiting for user to begin.
        WaitToBegin = 0,
        /// Active rowing.
        WorkoutRow = 1,
        /// Countdown pause between intervals.
        CountdownPause = 2,
        /// Rest period between intervals.
        IntervalRest = 3,
        /// Interval work (time target).
        IntervalWorkTime = 4,
        /// Interval work (distance target).
        IntervalWorkDistance = 5,
        /// Transitioning from rest to work (time).
        IntervalRestEndToWorkTime = 6,
        /// Transitioning from rest to work (distance).
        IntervalRestEndToWorkDistance = 7,
        /// Transitioning from work to rest (time).
        IntervalWorkTimeToRest = 8,
        /// Transitioning from work to rest (distance).
        IntervalWorkDistanceToRest = 9,
        /// Workout complete.
        WorkoutEnd = 10,
        /// Workout terminated.
        Terminate = 11,
        /// Workout has been logged.
        WorkoutLogged = 12,
        /// Erg re-arming for next workout.
        Rearm = 13,
    }
}

csafe_enum! {
    /// Whether the flywheel is spinning.
    RowingState {
        /// Flywheel not spinning.
        Inactive = 0,
        /// Flywheel spinning.
        Active = 1,
    }
}

csafe_enum! {
    /// Current phase of the rowing stroke.
    StrokeState {
        /// Waiting for wheel to reach minimum speed.
        WaitingForWheelToReachMinSpeed = 0,
        /// Waiting for wheel to accelerate.
        WaitingForWheelToAccelerate = 1,
        /// Drive phase.
        Driving = 2,
        /// Dwelling after drive.
        DwellingAfterDrive = 3,
        /// Recovery phase.
        Recovery = 4,
    }
}

csafe_enum! {
    /// Duration measurement unit for workout targets.
    DurationType {
        /// Time-based.
        Time = 0x00,
        /// Calorie-based.
        Calories = 0x40,
        /// Distance-based.
        Distance = 0x80,
        /// Watt-minute-based.
        WattMinutes = 0xC0,
    }
}

csafe_enum! {
    /// Screen displayed on the PM.
    ScreenType {
        /// No screen / off.
        None = 0,
        /// Workout screen.
        Workout = 1,
        /// Race screen.
        Race = 2,
        /// CSAFE screen.
        Csafe = 3,
        /// Diagnostics screen.
        Diag = 4,
        /// Manufacturing screen.
        Mfg = 5,
    }
}

csafe_enum! {
    /// Concept2 ergometer machine type.
    ErgMachineType {
        /// Model D (static).
        StaticD = 0,
        /// Model C (static).
        StaticC = 1,
        /// Model A (static).
        StaticA = 2,
        /// Model B (static).
        StaticB = 3,
        /// Model E (static).
        StaticE = 5,
        /// Simulator (static).
        StaticSimulator = 7,
        /// Dynamic (static mount).
        StaticDynamic = 8,
        /// Slides Model A.
        SlidesA = 16,
        /// Slides Model B.
        SlidesB = 17,
        /// Slides Model C.
        SlidesC = 18,
        /// Slides Model D.
        SlidesD = 19,
        /// Slides Model E.
        SlidesE = 20,
        /// Linked dynamic.
        LinkedDynamic = 32,
        /// Dyno (static).
        StaticDyno = 64,
        /// SkiErg (static).
        StaticSki = 128,
        /// SkiErg simulator (static).
        StaticSkiSimulator = 143,
        /// BikeErg.
        Bike = 192,
        /// BikeErg with arms.
        BikeArms = 193,
        /// BikeErg without arms.
        BikeNoArms = 194,
        /// BikeErg simulator.
        BikeSimulator = 207,
        /// Multi-erg row.
        MultiergRow = 224,
        /// Multi-erg ski.
        MultiergSki = 225,
        /// Multi-erg bike.
        MultiergBike = 226,
    }
}
