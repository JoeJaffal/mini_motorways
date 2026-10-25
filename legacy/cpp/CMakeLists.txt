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
set_target_properties(mini_motorways_rl PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}")
if(BUILD_TESTING)
    add_executable(construction_tests construction_tests.cpp mini_motorways_env.cpp renderer.cpp)
    target_compile_definitions(construction_tests PRIVATE NOMINMAX)
    target_link_libraries(construction_tests PRIVATE OpenGL::GL glfw GLEW::GLEW glm::glm)
    set_target_properties(construction_tests PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}")
    add_test(NAME construction_economy COMMAND construction_tests)
endif()
