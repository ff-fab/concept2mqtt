# Changelog

## [0.1.1](https://github.com/ff-fab/concept2mqtt/compare/v0.1.0...v0.1.1) (2026-09-12)


### Features

* :sparkles: initial commit ([342a5a0](https://github.com/ff-fab/concept2mqtt/commit/342a5a004f81313c293a45c1177d7c5ce29351cc))
* add claude code wiggum script ([#15](https://github.com/ff-fab/concept2mqtt/issues/15)) ([0aa4e89](https://github.com/ff-fab/concept2mqtt/commit/0aa4e8931b0eb36d22de24ff642e3baba86f944b))
* add PM5 dual BLE connection PoC test script ([1a743e3](https://github.com/ff-fab/concept2mqtt/commit/1a743e3d80a85d8c7c3981f7d26f3068046da78a))
* add Rust code coverage to CI pipeline ([#18](https://github.com/ff-fab/concept2mqtt/issues/18)) ([9397690](https://github.com/ff-fab/concept2mqtt/commit/93976903a02d02441b6b51edf1569c0577c58232))
* add YAML test vectors and parametrized BLE decoder runner ([#17](https://github.com/ff-fab/concept2mqtt/issues/17)) ([5c5c55b](https://github.com/ff-fab/concept2mqtt/commit/5c5c55b5a02195483a08e7f1a7a36cce89b06466))
* BleakPm5Adapter — real BLE adapter for PM5 ([#24](https://github.com/ff-fab/concept2mqtt/issues/24)) ([108738c](https://github.com/ff-fab/concept2mqtt/commit/108738c5183fd687393a83b553b91d11223bf451))
* **ble:** PM5 BLE peripheral relay — implementation + first two hardware validation rounds ([#21](https://github.com/ff-fab/concept2mqtt/issues/21)) ([2d885fe](https://github.com/ff-fab/concept2mqtt/commit/2d885fe77d04b459b481ab578b0e6cf86a0e5548))
* CSAFE command encoding with zero-alloc buffers ([c399eee](https://github.com/ff-fab/concept2mqtt/commit/c399eee6fa6586f2d8fc29c1abd2ba92a37b809e))
* define CSAFE command types with PyO3 bindings ([#8](https://github.com/ff-fab/concept2mqtt/issues/8)) ([b1f1b36](https://github.com/ff-fab/concept2mqtt/commit/b1f1b362d63c9adffc0d787046dc71a4392af7a1))
* expose BLE decoders and CSAFE response parser to Python via PyO3 ([#14](https://github.com/ff-fab/concept2mqtt/issues/14)) ([24e792f](https://github.com/ff-fab/concept2mqtt/commit/24e792fa2bf002e8a161e729c5aea2331f244a14))
* expose command builders to Python via PyO3 wrapper classes ([#11](https://github.com/ff-fab/concept2mqtt/issues/11)) ([331d4c9](https://github.com/ff-fab/concept2mqtt/commit/331d4c9694bffef201f8dd7611b5728669598198))
* expose framing constants to Python, add binding test suite ([#6](https://github.com/ff-fab/concept2mqtt/issues/6)) ([8ad0ef7](https://github.com/ff-fab/concept2mqtt/commit/8ad0ef73255ae6d4f48fbea95370e5dc440da096))
* expose framing constants to Python, add binding test suite ([#6](https://github.com/ff-fab/concept2mqtt/issues/6)) ([dd217dd](https://github.com/ff-fab/concept2mqtt/commit/dd217dddec2417f61f127e7e15e6d9b3af891a31))
* implement BLE notification decoders for all PM5 rowing characteristics ([#13](https://github.com/ff-fab/concept2mqtt/issues/13)) ([0f240c3](https://github.com/ff-fab/concept2mqtt/commit/0f240c3f1f2cab1c4f7d0e953d19159e26ff67c8))
* implement CSAFE byte stuffing (stuff_bytes/unstuff_bytes) ([#2](https://github.com/ff-fab/concept2mqtt/issues/2)) ([edc68ba](https://github.com/ff-fab/concept2mqtt/commit/edc68ba82a78818b15130dda542a4b0bc3c99189))
* implement CSAFE response parser ([#12](https://github.com/ff-fab/concept2mqtt/issues/12)) ([09cf309](https://github.com/ff-fab/concept2mqtt/commit/09cf3095f50be03325d0518c2f976878cce81bb3))
* implement CSAFE XOR checksum (compute + validate) ([#3](https://github.com/ff-fab/concept2mqtt/issues/3)) ([c355688](https://github.com/ff-fab/concept2mqtt/commit/c3556880a321bc15b32b463aa1a2356b51f92e97))
* implement extended frame support (build, parse, auto-detect) ([#7](https://github.com/ff-fab/concept2mqtt/issues/7)) ([79f9d22](https://github.com/ff-fab/concept2mqtt/commit/79f9d22da4011998b20e63573b5af45d97ee6a95))
* implement standard CSAFE frame builder ([#4](https://github.com/ff-fab/concept2mqtt/issues/4)) ([d3f0371](https://github.com/ff-fab/concept2mqtt/commit/d3f03713d9f2400c986eaf4fe38033ec14ac684d))
* implement standard frame parser with error conversion ([#5](https://github.com/ff-fab/concept2mqtt/issues/5)) ([da40cac](https://github.com/ff-fab/concept2mqtt/commit/da40cacfaca115bb883520d881be78f23bd17ffe))
* Rust toolchain — scaffold, local dev & CI ([#1](https://github.com/ff-fab/concept2mqtt/issues/1)) ([dc2ee8a](https://github.com/ff-fab/concept2mqtt/commit/dc2ee8ad0669a1ff70e8d47e4d076265482b857c))
* scaffold cosalette app with Pm5Port hexagonal architecture ([ef73b36](https://github.com/ff-fab/concept2mqtt/commit/ef73b36d93bd84878389facc78a17376b899aeac))
* scaffold cosalette app with Pm5Port hexagonal architecture ([e6d8a66](https://github.com/ff-fab/concept2mqtt/commit/e6d8a66937d5376f7d7da499e5f6feca10ae1441))
* wire BleakPm5Adapter and add workout lifecycle state machine ([#25](https://github.com/ff-fab/concept2mqtt/issues/25)) ([8cb8c73](https://github.com/ff-fab/concept2mqtt/commit/8cb8c73987810fc4086c8966beb8fbcc3c8e672a))


### Bug Fixes

* address pm5 scaffold review findings ([75c9562](https://github.com/ff-fab/concept2mqtt/commit/75c95621f7a3628e2a49992b5831e1ff3d87d906))
* update README for source link and correct file path ([8c9ce9d](https://github.com/ff-fab/concept2mqtt/commit/8c9ce9d4ddc63149d2517cee58be4e250a985bfc))
