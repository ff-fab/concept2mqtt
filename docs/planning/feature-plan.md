# Feature Plan - rough first draft

- **Get all (historical) training data**:

  I want to get all saved training data from the PM5, including workouts, workout logs,
  and user profiles. This will allow me to analyze my training history and identify
  patterns or areas for improvement.

  *The challenges:*

  We need to cleanly analyze when and how this gets triggered. The PM5 already contains
  training data that is not yet extracted, and with every training new data will be
  added. Potentially old data could also get deleted or compressed by the PM5 firmware,
  but that shall not effect the already extracted data.

  Master data shall be the data stored by the smart home system reading from the MQTT
  topics provided by our app. The PM5 data is the source of truth, and we want to make
  sure we have a complete and accurate copy of it in our system at all times.

  Data synchronization between PM5, this app and the smart home system will be a key
  aspect to consider.

  Timing will has to be carefully considered. We want to avoid overwhelming the PM5 with
  too many requests. Also the PM5 is usually hibernating, only waking up when the user
  interacts with it or starts a training on the rowing machine. Whether this can be
  somehow trigger our app or if we have to constantly poll the PM5 for availability or
  new data is something we need to figure out. We shall not drain the PM5 battery by
  keeping it constantly awake or by sending too many requests that could wake it up.

- **Get live training data**:

  I want to get live training data from the PM5 while I am rowing, including metrics
  like pace, stroke rate, distance, and heart rate.

  I want to use the data provided by this app also to build another standalone app that
  monitors the live training data and provides real-time feedback and coaching to help
  me improve, and also to visualize my training data in a more engaging way, such as
  competing against former workouts or against other users.


**Constrains:**

We want to use the cosalette framework (https://ff-fab.github.io/cosalette/) to build
this app.

We can test any concepts and implementations with a real PM5 and a
raspberry pi zero W1.1 with python 3.13.5 on trixie with uv and bleak installed, that
connects to it via bluetooth. The folder `docs/planning/legacy` contains a simple smoke
test we currently use to test this.

The tests have to be conducted in a different environment though and cannot be
automatically done in this project.

Test scripts we need to test or validate behaviour of the PM5 have to be prepared in a
way that they can be handed over to the demo project that has the real hardware.

The test strategy of this project shall not rely on the other project, this is just for
validation and information gathering during concept phase and implementation.

The CSAFE specification provided by Concept2 for the PM5 is provided in
machine-readable YAML format in the `docs/planning/spec/csafe` folder.

The target hardware to use to connect to the PM5 is not finalized yet, but will likely
be a Raspberry Pi Zero 2 W with python 3.13.5 on trixie.

A more powerful raspberry pi e.g. a Pi 4 or Pi 5 could be targeted if the required
resource usage of the app exceeds the capabilities of the Pi Zero, but we want to aim
for the lowest possible hardware requirements to keep the cost and energy consumption
low.
