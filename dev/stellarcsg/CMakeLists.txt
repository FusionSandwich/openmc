cmake_minimum_required(VERSION 3.16)
project(stellarcsg_reference_kernel LANGUAGES CXX)

option(STELLARCSG_BUILD_TESTS "Build StellarCSG tests" ON)
option(STELLARCSG_BUILD_BENCHMARKS "Build geometry microbenchmarks" ON)
option(STELLARCSG_BUILD_TOOLS "Build local inspection tools" ON)
option(STELLARCSG_ENABLE_HDF5 "Build the coefficient-file HDF5 adapter" ON)
option(STELLARCSG_ENABLE_SANITIZERS "Enable ASan/UBSan for standalone tests" OFF)

add_library(stellarcsg_reference STATIC
  src/periodic_radial_surface.cpp
  src/root_solver.cpp
  src/uniform_periodic_bicubic_spline.cpp
  src/uniform_periodic_cubic_spline.cpp
  src/compiled_periodic_surface.cpp
)
add_library(StellarCSG::reference ALIAS stellarcsg_reference)
target_compile_features(stellarcsg_reference PUBLIC cxx_std_17)
target_include_directories(stellarcsg_reference PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>)

if(STELLARCSG_ENABLE_HDF5)
  find_package(HDF5 REQUIRED COMPONENTS C HL)
  target_sources(stellarcsg_reference PRIVATE src/coefficient_file.cpp)
  target_include_directories(stellarcsg_reference PUBLIC ${HDF5_INCLUDE_DIRS})
  target_link_libraries(stellarcsg_reference PUBLIC
    ${HDF5_LIBRARIES} ${HDF5_HL_LIBRARIES})
  target_compile_definitions(stellarcsg_reference PUBLIC STELLARCSG_HAS_HDF5)
endif()

if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(stellarcsg_reference PRIVATE
    -Wall -Wextra -Wpedantic -Wconversion -Wshadow)
  if(STELLARCSG_ENABLE_SANITIZERS)
    target_compile_options(stellarcsg_reference PRIVATE
      -fsanitize=address,undefined -fno-omit-frame-pointer)
    target_link_options(stellarcsg_reference PRIVATE
      -fsanitize=address,undefined)
  endif()
elseif(MSVC)
  target_compile_options(stellarcsg_reference PRIVATE /W4 /permissive-)
endif()

if(STELLARCSG_BUILD_TESTS)
  enable_testing()

  add_executable(stellarcsg_reference_tests
    tests/test_reference_kernel.cpp)
  target_link_libraries(stellarcsg_reference_tests
    PRIVATE StellarCSG::reference)
  target_compile_features(stellarcsg_reference_tests PRIVATE cxx_std_17)
  add_test(NAME stellarcsg_reference_tests
    COMMAND stellarcsg_reference_tests)

  add_executable(stellarcsg_compiled_surface_tests
    tests/test_compiled_surface.cpp)
  target_link_libraries(stellarcsg_compiled_surface_tests
    PRIVATE StellarCSG::reference)
  target_compile_features(stellarcsg_compiled_surface_tests PRIVATE cxx_std_17)
  add_test(NAME stellarcsg_compiled_surface_tests
    COMMAND stellarcsg_compiled_surface_tests)

  if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    foreach(target stellarcsg_reference_tests stellarcsg_compiled_surface_tests)
      target_compile_options(${target} PRIVATE
        -Wall -Wextra -Wpedantic -Wconversion -Wshadow)
      if(STELLARCSG_ENABLE_SANITIZERS)
        target_compile_options(${target} PRIVATE
          -fsanitize=address,undefined -fno-omit-frame-pointer)
        target_link_options(${target} PRIVATE
          -fsanitize=address,undefined)
      endif()
    endforeach()
  endif()
endif()

if(STELLARCSG_BUILD_BENCHMARKS)
  add_executable(stellarcsg_surface_benchmark
    benchmarks/benchmark_compiled_surface.cpp)
  target_link_libraries(stellarcsg_surface_benchmark
    PRIVATE StellarCSG::reference)
  target_compile_features(stellarcsg_surface_benchmark PRIVATE cxx_std_17)
endif()

if(STELLARCSG_BUILD_TOOLS)
  add_executable(stellarcsg_inspect_surface tools/inspect_surface.cpp)
  target_link_libraries(stellarcsg_inspect_surface PRIVATE StellarCSG::reference)
  target_compile_features(stellarcsg_inspect_surface PRIVATE cxx_std_17)
endif()
