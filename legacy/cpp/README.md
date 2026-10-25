# Legacy C++ playground

This is the older C++17/OpenGL playground. The active Original and Custom apps live in [simulation/](../../simulation/). These implementations do not share a simulation engine or guarantee equivalent behavior.

The earlier playground comes from the repository's [MiniMotorwaysRL upstream](https://github.com/KTK-Jadoo/mini_motorways_rl), with local changes retained here. It should not be confused with the independently implemented Unity reconstruction.

The local changes retained here remove motorway actions, use unlimited construction with cumulative spending, add the construction-economy regression check, and update the renderer. Legacy prices remain road 1, traffic light 5 additional, bridge 10 and roundabout 8. The active Unity Custom app uses road 2.

## Build and test

Install CMake, a C++17 compiler, OpenGL, GLFW, GLEW and GLM. On Windows these libraries can be supplied through vcpkg. Run from the repository root:

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release
ctest --test-dir build -C Release --output-on-failure
```

For Windows, add `-DCMAKE_TOOLCHAIN_FILE=<vcpkg>/scripts/buildsystems/vcpkg.cmake` when configuring. Executables stay in `build/` for single-configuration generators or `build/Release/` for Visual Studio.

`mini_motorways_rl demo` runs the interactive random-agent demo. `mini_motorways_rl train 100` runs 100 random-agent episodes; despite the historical command name, it does not train a learning policy. `construction_tests` runs without opening a graphics window. Its optional `--preview` mode opens graphics and writes a local `preview.bmp`.

[The archived guide](../../docs/LEGACY_PLAYGROUND.md) contains historical claims, commands and benchmark figures. It is not the current implementation specification.
