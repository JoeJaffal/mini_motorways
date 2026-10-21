cmake_minimum_required(VERSION 3.16)
project(MiniMotorwaysRL LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(OpenGL REQUIRED)
find_package(glfw3 CONFIG REQUIRED)
find_package(GLEW REQUIRED)
find_package(glm CONFIG REQUIRED)

add_executable(mini_motorways_rl
    main.cpp
    renderer.cpp
    mini_motorways_env.cpp
)

target_compile_definitions(mini_motorways_rl PRIVATE NOMINMAX)
target_link_libraries(mini_motorways_rl PRIVATE
    OpenGL::GL glfw GLEW::GLEW glm::glm
)