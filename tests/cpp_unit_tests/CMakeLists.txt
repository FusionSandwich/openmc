set(TEST_NAMES
  test_distribution
  test_file_utils
  test_tally
  test_interpolate
  test_math
  test_mcpl_stat_sum
  test_mesh
  test_photon
  test_ray
  test_region
  test_tensor
  test_geometry
  # Add additional unit test files here
)

if(OPENMC_ENABLE_EXPERIMENTAL_STELLARCSG)
  list(APPEND TEST_NAMES test_stellarcsg_surface)
endif()

foreach(test ${TEST_NAMES})
  add_executable(${test} ${test}.cpp)
  target_link_libraries(${test} Catch2::Catch2WithMain libopenmc)
  add_test(NAME ${test} COMMAND ${test} WORKING_DIRECTORY ${UNIT_TEST_BIN_OUTPUT_DIR})
endforeach()

if(OPENMC_ENABLE_EXPERIMENTAL_STELLARCSG)
  target_compile_definitions(test_stellarcsg_surface PRIVATE
    STELLARCSG_SOURCE_DIR="${CMAKE_SOURCE_DIR}")
endif()
