cmake_minimum_required(VERSION 3.16)

project(stellarcsg_reference_kernel LANGUAGES CXX)

option(STELLARCSG_BUILD_TESTS "Build the standalone StellarCSG tests" ON)

add_library(stellarcsg_reference STATIC
  src/periodic_radial_surface.cpp
  src/root_solver.cpp
  src/uniform_periodic_bicubic_spline.cpp
)

add_library(StellarCSG::reference ALIAS stellarcsg_reference)

target_compile_features(stellarcsg_reference PUBLIC cxx_std_17)
target_include_directories(stellarcsg_reference
  PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)

if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(stellarcsg_reference PRIVATE
    -Wall -Wextra -Wpedantic -Wconversion -Wshadow
  )
elseif(MSVC)
  target_compile_options(stellarcsg_reference PRIVATE /W4 /permissive-)
endif()

if(STELLARCSG_BUILD_TESTS)
  enable_testing()
  add_executable(stellarcsg_reference_tests tests/test_reference_kernel.cpp)
  target_link_libraries(stellarcsg_reference_tests PRIVATE StellarCSG::reference)
  target_compile_features(stellarcsg_reference_tests PRIVATE cxx_std_17)
  if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(stellarcsg_reference_tests PRIVATE
      -Wall -Wextra -Wpedantic -Wconversion -Wshadow
    )
  elseif(MSVC)
    target_compile_options(stellarcsg_reference_tests PRIVATE /W4 /permissive-)
  endif()
  add_test(NAME stellarcsg_reference_tests COMMAND stellarcsg_reference_tests)
endif()
