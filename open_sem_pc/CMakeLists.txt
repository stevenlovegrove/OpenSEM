cmake_minimum_required(VERSION 3.18)
project(SEM)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Threads REQUIRED)
find_package(Pangolin 0.4 REQUIRED)
include_directories(${Pangolin_INCLUDE_DIRS})

add_subdirectory(serial)
add_subdirectory(asyncplusplus)

add_executable(SEM main.cpp)

target_link_libraries(SEM Threads::Threads serial Async++ pango_display pango_plot pango_image)
target_include_directories(SEM PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/serial/include)

# FTDI Library
target_include_directories(SEM PRIVATE "/Users/stevenlovegrove/code/ftdi")
target_link_libraries(SEM "/usr/local/lib/libftd3xx.dylib")



add_executable(dac dac_test.cpp)
target_link_libraries(dac Threads::Threads Async++ pango_display pango_plot pango_image)
