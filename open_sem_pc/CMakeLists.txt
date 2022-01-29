cmake_minimum_required(VERSION 3.18)
project(SEM)

find_package(Pangolin 0.4 REQUIRED)
include_directories(${Pangolin_INCLUDE_DIRS})

add_subdirectory(serial)
add_subdirectory(asyncplusplus)

add_executable(SEM main.cpp)
target_link_libraries(SEM serial Async++ pango_display pango_python)
target_include_directories(SEM PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/serial/include)
