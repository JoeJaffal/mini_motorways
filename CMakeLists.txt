cmake_minimum_required(VERSION 3.16)
project(MiniMotorwaysPlayground LANGUAGES CXX)

# The active simulator is the Unity/.NET project in simulation/.
# Keep root CMake commands compatible with the separate legacy C++ playground.
include(CTest)
add_subdirectory(legacy/cpp)
