# Changelog

## [0.1.1](https://github.com/ff-fab/concept2mqtt/compare/v0.1.0...v0.1.1) (2026-05-02)


### Features

* :sparkles: initial commit ([342a5a0](https://github.com/ff-fab/concept2mqtt/commit/342a5a004f81313c293a45c1177d7c5ce29351cc))
* add claude code wiggum script ([#15](https://github.com/ff-fab/concept2mqtt/issues/15)) ([33a81d7](https://github.com/ff-fab/concept2mqtt/commit/33a81d7c35d6dbb5a804c84793b6621531eaa244))
* add Rust code coverage to CI pipeline ([#18](https://github.com/ff-fab/concept2mqtt/issues/18)) ([60baf4f](https://github.com/ff-fab/concept2mqtt/commit/60baf4f603b1e97427c0b1c75bbcd063aeffb4b9))
* add YAML test vectors and parametrized BLE decoder runner ([#17](https://github.com/ff-fab/concept2mqtt/issues/17)) ([9c39e36](https://github.com/ff-fab/concept2mqtt/commit/9c39e363b9f27fd153c4a904be705fb6596212f4))
* CSAFE command encoding with zero-alloc buffers ([aac591c](https://github.com/ff-fab/concept2mqtt/commit/aac591c5fc53c3a80247f457f4520796b9d12e67))
* define CSAFE command types with PyO3 bindings ([#8](https://github.com/ff-fab/concept2mqtt/issues/8)) ([e9a131e](https://github.com/ff-fab/concept2mqtt/commit/e9a131e119923e9f9990a2d9e05ab51790550e82))
* expose BLE decoders and CSAFE response parser to Python via PyO3 ([#14](https://github.com/ff-fab/concept2mqtt/issues/14)) ([8e49166](https://github.com/ff-fab/concept2mqtt/commit/8e49166307cee23fde4854ea9fb28e33badb338f))
* expose command builders to Python via PyO3 wrapper classes ([#11](https://github.com/ff-fab/concept2mqtt/issues/11)) ([30312d4](https://github.com/ff-fab/concept2mqtt/commit/30312d445e2b70fb1597c061e9591b939130c6c4))
* expose framing constants to Python, add binding test suite ([#6](https://github.com/ff-fab/concept2mqtt/issues/6)) ([77d2222](https://github.com/ff-fab/concept2mqtt/commit/77d2222bc41c9e30f17f060b0e9031f37f58ef1c))
* expose framing constants to Python, add binding test suite ([#6](https://github.com/ff-fab/concept2mqtt/issues/6)) ([fc24f1d](https://github.com/ff-fab/concept2mqtt/commit/fc24f1d2f18e82b264c24ac072749969e032845a))
* implement BLE notification decoders for all PM5 rowing characteristics ([#13](https://github.com/ff-fab/concept2mqtt/issues/13)) ([0243c08](https://github.com/ff-fab/concept2mqtt/commit/0243c08b3ddd801d5cec16ec7b51e603ff60a7f1))
* implement CSAFE byte stuffing (stuff_bytes/unstuff_bytes) ([#2](https://github.com/ff-fab/concept2mqtt/issues/2)) ([f2c774f](https://github.com/ff-fab/concept2mqtt/commit/f2c774f6bb0c8dd73e15776a38c55ae4842b1842))
* implement CSAFE response parser ([#12](https://github.com/ff-fab/concept2mqtt/issues/12)) ([018c541](https://github.com/ff-fab/concept2mqtt/commit/018c541aa078e270f029093e3d97e6002c022e4a))
* implement CSAFE XOR checksum (compute + validate) ([#3](https://github.com/ff-fab/concept2mqtt/issues/3)) ([4ece0dc](https://github.com/ff-fab/concept2mqtt/commit/4ece0dcaf4f75a010635723258cf2a28b90790cd))
* implement extended frame support (build, parse, auto-detect) ([#7](https://github.com/ff-fab/concept2mqtt/issues/7)) ([19ba6f8](https://github.com/ff-fab/concept2mqtt/commit/19ba6f8f6a975b23fb486ecf9706a5560793de34))
* implement standard CSAFE frame builder ([#4](https://github.com/ff-fab/concept2mqtt/issues/4)) ([271f8ca](https://github.com/ff-fab/concept2mqtt/commit/271f8ca3ccef4ad3e140cf12af5deee79c34dab0))
* implement standard frame parser with error conversion ([#5](https://github.com/ff-fab/concept2mqtt/issues/5)) ([82936d1](https://github.com/ff-fab/concept2mqtt/commit/82936d1c7b576fb389be5c6c3b29211938f04338))
* Rust toolchain — scaffold, local dev & CI ([#1](https://github.com/ff-fab/concept2mqtt/issues/1)) ([c7a7bd2](https://github.com/ff-fab/concept2mqtt/commit/c7a7bd259594da30e03866f3030037f1aff103b5))


### Bug Fixes

* update README for source link and correct file path ([8c9ce9d](https://github.com/ff-fab/concept2mqtt/commit/8c9ce9d4ddc63149d2517cee58be4e250a985bfc))
