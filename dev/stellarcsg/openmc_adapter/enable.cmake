# Opt-in OpenMC integration for the isolated StellarCSG development branch.
# Invoke from the OpenMC repository root with:
#
# cmake -S . -B build/openmc-stellarcsg \
#   -DCMAKE_PROJECT_INCLUDE=$PWD/dev/stellarcsg/openmc_adapter/enable.cmake \
#   -DSTELLARCSG_BUILD_OPENMC_ADAPTER_TESTS=ON
#
# Ordinary OpenMC builds are unchanged. The injector verifies source anchors,
# generates a patched copy of src/surface.cpp in the build directory, and adds
# only the experimental wrapper/kernel sources to libopenmc.

if(STELLARCSG_OPENMC_INJECTION_CONFIGURED)
  return()
endif()
if(NOT CMAKE_PROJECT_NAME STREQUAL "openmc")
  return()
endif()
set(STELLARCSG_OPENMC_INJECTION_CONFIGURED TRUE)

option(STELLARCSG_BUILD_OPENMC_ADAPTER_TESTS
  "Build the experimental periodic-spline OpenMC adapter test" ON)

if(STELLARCSG_BUILD_OPENMC_ADAPTER_TESTS)
  enable_testing()
endif()

set(_stellarcsg_root "${CMAKE_SOURCE_DIR}/dev/stellarcsg")
set(_stellarcsg_generated_dir "${CMAKE_BINARY_DIR}/generated/stellarcsg")
file(MAKE_DIRECTORY "${_stellarcsg_generated_dir}")

file(READ "${CMAKE_SOURCE_DIR}/src/surface.cpp" _stellarcsg_surface_source)
set(_stellarcsg_include_anchor "#include \"openmc/surface.h\"")
string(FIND "${_stellarcsg_surface_source}"
  "${_stellarcsg_include_anchor}" _stellarcsg_include_location)
if(_stellarcsg_include_location EQUAL -1)
  message(FATAL_ERROR
    "StellarCSG integration anchor missing from src/surface.cpp: include")
endif()
string(REPLACE "${_stellarcsg_include_anchor}"
  "${_stellarcsg_include_anchor}\n#include \"openmc/surface_periodic_spline.h\""
  _stellarcsg_surface_source "${_stellarcsg_surface_source}")

set(_stellarcsg_parser_anchor [=[      } else if (surf_type == "z-torus") {
        model::surfaces.push_back(std::make_unique<SurfaceZTorus>(surf_node));

      } else {]=])
set(_stellarcsg_parser_replacement [=[      } else if (surf_type == "z-torus") {
        model::surfaces.push_back(std::make_unique<SurfaceZTorus>(surf_node));

      } else if (surf_type == "periodic-spline") {
        model::surfaces.push_back(
          make_unique<SurfacePeriodicSpline>(surf_node));

      } else {]=])
string(FIND "${_stellarcsg_surface_source}"
  "${_stellarcsg_parser_anchor}" _stellarcsg_parser_location)
if(_stellarcsg_parser_location EQUAL -1)
  message(FATAL_ERROR
    "StellarCSG integration anchor missing from src/surface.cpp: parser")
endif()
string(REPLACE "${_stellarcsg_parser_anchor}"
  "${_stellarcsg_parser_replacement}"
  _stellarcsg_surface_source "${_stellarcsg_surface_source}")

set(_stellarcsg_generated_surface
  "${_stellarcsg_generated_dir}/surface_stellarcsg.cpp")
file(WRITE "${_stellarcsg_generated_surface}"
  "${_stellarcsg_surface_source}")

function(_stellarcsg_finalize_openmc_target)
  if(NOT TARGET libopenmc)
    message(FATAL_ERROR "StellarCSG injection could not find libopenmc target")
  endif()

  get_target_property(_stellarcsg_sources libopenmc SOURCES)
  list(REMOVE_ITEM _stellarcsg_sources
    "src/surface.cpp" "${CMAKE_SOURCE_DIR}/src/surface.cpp")
  set_property(TARGET libopenmc PROPERTY SOURCES "${_stellarcsg_sources}")

  target_sources(libopenmc PRIVATE
    "${_stellarcsg_generated_surface}"
    "${_stellarcsg_root}/src/periodic_radial_surface.cpp"
    "${_stellarcsg_root}/src/root_solver.cpp"
    "${_stellarcsg_root}/src/uniform_periodic_cubic_spline.cpp"
    "${_stellarcsg_root}/src/uniform_periodic_bicubic_spline.cpp"
    "${_stellarcsg_root}/src/compiled_periodic_surface.cpp"
    "${_stellarcsg_root}/src/coefficient_file.cpp"
    "${_stellarcsg_root}/openmc_adapter/src/surface_periodic_spline.cpp")
  target_include_directories(libopenmc PRIVATE
    "${_stellarcsg_root}/include"
    "${_stellarcsg_root}/openmc_adapter/include")
  target_compile_definitions(libopenmc PRIVATE OPENMC_EXPERIMENTAL_STELLARCSG STELLARCSG_HAS_HDF5)

  if(STELLARCSG_BUILD_OPENMC_ADAPTER_TESTS)
    add_executable(stellarcsg_openmc_adapter_tests
      "${_stellarcsg_root}/openmc_adapter/tests/test_periodic_spline_surface.cpp")
    target_compile_features(stellarcsg_openmc_adapter_tests PRIVATE cxx_std_17)
    target_include_directories(stellarcsg_openmc_adapter_tests PRIVATE
      "${_stellarcsg_root}/include"
      "${_stellarcsg_root}/openmc_adapter/include")
    target_compile_definitions(stellarcsg_openmc_adapter_tests PRIVATE
      STELLARCSG_HAS_HDF5)
    target_link_libraries(stellarcsg_openmc_adapter_tests PRIVATE libopenmc)
    add_test(NAME stellarcsg_openmc_adapter_tests
      COMMAND stellarcsg_openmc_adapter_tests)
  endif()
endfunction()

cmake_language(DEFER DIRECTORY "${CMAKE_SOURCE_DIR}"
  CALL _stellarcsg_finalize_openmc_target)

message(STATUS
  "StellarCSG experimental OpenMC adapter enabled (ordinary builds unchanged)")
