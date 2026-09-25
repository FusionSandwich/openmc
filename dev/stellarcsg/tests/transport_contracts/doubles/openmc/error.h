#pragma once
#include <stdexcept>
#include <string>
namespace openmc {
[[noreturn]] inline void fatal_error(const std::string& message) {
  throw std::runtime_error("FATAL_TEST_DOUBLE: " + message);
}
}
