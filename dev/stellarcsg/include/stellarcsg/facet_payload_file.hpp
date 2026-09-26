#ifndef STELLARCSG_FACET_PAYLOAD_FILE_HPP
#define STELLARCSG_FACET_PAYLOAD_FILE_HPP

#include "stellarcsg/compiled_facet_surface_set.hpp"

#include <string>
#include <vector>

namespace stellarcsg {

struct FacetPayloadData {
  std::vector<FacetTriangle> triangles;
  std::string canonical_metadata_json;
  std::string content_id;
};

[[nodiscard]] std::string facet_payload_content_id(const FacetPayloadData& data);
[[nodiscard]] FacetPayloadData read_facet_payload_hdf5(
  const std::string& filename, const std::string& dataset,
  const std::string& expected_content_id = {});

} // namespace stellarcsg

#endif
