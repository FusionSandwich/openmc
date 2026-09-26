// Export the actual compiled swept-span BVH topology and boxes for audit.
#include "stellarcsg/compiled_swept_surface.hpp"
#include "stellarcsg/swept_coefficient_file.hpp"

#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>

namespace {

std::string hex(double value)
{
  std::ostringstream out;
  out << std::hexfloat << value;
  return out.str();
}

void box_fields(const char* prefix, const stellarcsg::BoundingBox& box)
{
  std::cout << ",\"" << prefix << "_lower_hex\":[\""
            << hex(box.lower.x) << "\",\"" << hex(box.lower.y) << "\",\""
            << hex(box.lower.z) << "\"],\"" << prefix
            << "_upper_hex\":[\"" << hex(box.upper.x) << "\",\""
            << hex(box.upper.y) << "\",\"" << hex(box.upper.z) << "\"]";
}

void member(const std::string& path, int id)
{
  const std::string dataset = "/coils/coil_00" + std::to_string(id);
  const auto data =
    stellarcsg::read_swept_spline_surface_hdf5(path, dataset);
  const stellarcsg::CompiledSweptSplineSurface surface {data, true};
  const auto& spans = surface.spans();
  const auto& indices = surface.span_indices();
  const auto& nodes = surface.span_bvh();
  if (spans.size() != data.sample_count || indices.size() != spans.size()
      || nodes.empty()) {
    throw std::runtime_error("unexpected compiled BVH dimensions");
  }

  std::cout << "{\"record\":\"meta\",\"member\":" << id
            << ",\"dataset\":\"" << dataset << "\",\"sample_count\":"
            << data.sample_count << ",\"span_count\":" << spans.size()
            << ",\"index_count\":" << indices.size() << ",\"node_count\":"
            << nodes.size() << ",\"root\":0";
  box_fields("surface", surface.bounding_box());
  std::cout << "}\n";

  std::cout << "{\"record\":\"indices\",\"member\":" << id
            << ",\"span_indices\":[";
  for (std::size_t slot = 0; slot < indices.size(); ++slot) {
    if (slot) std::cout << ',';
    std::cout << indices[slot];
  }
  std::cout << "]}\n";

  for (std::size_t span_id = 0; span_id < spans.size(); ++span_id) {
    const auto& span = spans[span_id];
    std::cout << "{\"record\":\"span\",\"member\":" << id
              << ",\"span\":" << span_id;
    box_fields("centerline", span.centerline_bbox);
    box_fields("conservative", span.conservative_bbox);
    std::cout << "}\n";
  }

  for (std::size_t node_id = 0; node_id < nodes.size(); ++node_id) {
    const auto& node = nodes[node_id];
    std::cout << "{\"record\":\"node\",\"member\":" << id
              << ",\"node\":" << node_id << ",\"left\":" << node.left
              << ",\"right\":" << node.right << ",\"first\":" << node.first
              << ",\"count\":" << node.count << ",\"leaf\":"
              << (node.leaf() ? "true" : "false");
    box_fields("centerline", node.centerline_bbox);
    box_fields("conservative", node.bbox);
    std::cout << "}\n";
  }
}

} // namespace

int main(int argc, char** argv)
{
  try {
    if (argc != 2)
      throw std::invalid_argument("Usage: dump_compiled_span_bvh H5");
    member(argv[1], 2);
    member(argv[1], 3);
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
