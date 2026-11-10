# Third-party notices

The project's own code is licensed under the [MIT License](LICENSE). This does
not change the licenses or copyright notices of third-party dependencies.

## Bosch BMI08x SensorAPI

- Upstream: https://github.com/boschsensortec/BMI08x_SensorAPI
- Path: `vendor/BMI08x_SensorAPI`
- Pinned commit: `c1ed227e7bb7da1fa600bbd4e5c82d0da1eb416a`
- Copyright: Bosch Sensortec GmbH (see upstream file headers and license).
- License: BSD-3-Clause; preserved in `vendor/BMI08x_SensorAPI/LICENSE`.

The dependency is an unmodified Git submodule. Always clone recursively or run
`git submodule update --init --recursive`. The default build compiles
`bmi08a.c`, `bmi08g.c`, and `bmi08xa.c` directly; it does not require COINES.
Upstream license and notices must accompany redistributed source/binaries.

## Wiring reference

`wiring-reference.png` is an English annotation of the board photograph supplied
for this project, edited using OpenAI's built-in image generation tool.
Hardware names and logos in the photograph identify the pictured equipment;
they do not imply endorsement or affiliation.

## Hardware setup photograph

`docs/images/qcs6490-rubik-pi3-setup.png` is the user-supplied photograph of the
Qualcomm QCS6490-based RUBIK Pi 3 prototype. It is reproduced without edits.
Use the wiring table rather than inferring individual connections from this
overview photograph.
