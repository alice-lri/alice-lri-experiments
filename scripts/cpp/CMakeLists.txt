cmake_minimum_required(VERSION 3.20)
project(alice_lri_scripts_cpp VERSION 0.1.0 LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)

# Conan dependencies
include(${CMAKE_BINARY_DIR}/conan_toolchain.cmake)
find_package(SQLiteCpp REQUIRED)

find_package(nlohmann_json REQUIRED)
set(JSON_BuildTests OFF CACHE INTERNAL "")

# ALICE-LRI library
find_library(alice_lri_lib NAMES alice_lri PATHS "$ENV{ALICE_LRI_LIB_PATH}" NO_DEFAULT_PATH)

if(NOT alice_lri_lib)
    message(FATAL_ERROR "Could not find alice_lri library in $ENV{ALICE_LRI_LIB_PATH}")
endif()

add_library(alice_lri SHARED IMPORTED)
set_target_properties(alice_lri PROPERTIES IMPORTED_LOCATION "${alice_lri_lib}")
target_include_directories(alice_lri INTERFACE "$ENV{ALICE_LRI_INCLUDE_PATH}")

# Build sources
set(SRC_FILES utils/FileUtils.cpp)
set(HEADER_FILES utils/FileUtils.h)

add_executable(intrinsics_to_sql intrinsics_to_sql.cpp ${SRC_FILES} ${HEADER_FILES})
add_executable(measure_times measure_times.cpp ${SRC_FILES} ${HEADER_FILES})

target_link_libraries(intrinsics_to_sql PRIVATE alice_lri SQLiteCpp nlohmann_json::nlohmann_json)
target_link_libraries(measure_times PRIVATE alice_lri)
