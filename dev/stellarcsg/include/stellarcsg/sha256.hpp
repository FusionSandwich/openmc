#ifndef STELLARCSG_SHA256_HPP
#define STELLARCSG_SHA256_HPP

#include <cstddef>
#include <cstdint>
#include <string>

namespace stellarcsg {

class Sha256 {
public:
  Sha256();
  void update(const void* data, std::size_t size);
  [[nodiscard]] std::string hex_digest();

private:
  void transform(const std::uint8_t* block);

  std::uint32_t state_[8];
  std::uint8_t buffer_[64] {};
  std::size_t buffer_size_ {0};
  std::uint64_t total_size_ {0};
  bool finalized_ {false};
};

} // namespace stellarcsg

#endif
