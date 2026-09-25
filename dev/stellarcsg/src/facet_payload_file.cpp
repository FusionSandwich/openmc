#include "stellarcsg/facet_payload_file.hpp"

#ifdef STELLARCSG_HAS_HDF5

#include "stellarcsg/sha256.hpp"

#include <hdf5.h>

#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace stellarcsg {
namespace {

void require(bool condition, const std::string& message)
{
  if (!condition) throw std::runtime_error(message);
}

struct Handle {
  hid_t id {-1};
  herr_t (*close)(hid_t) {nullptr};
  Handle(hid_t id_, herr_t (*close_)(hid_t)) : id {id_}, close {close_} {}
  Handle(const Handle&) = delete;
  Handle& operator=(const Handle&) = delete;
  ~Handle() { if (id >= 0) close(id); }
};

std::string attribute(hid_t group, const char* name)
{
  Handle item {H5Aopen(group, name, H5P_DEFAULT), H5Aclose};
  require(item.id >= 0, std::string("Missing facet attribute ") + name);
  Handle type {H5Aget_type(item.id), H5Tclose};
  require(type.id >= 0 && H5Tget_class(type.id) == H5T_STRING,
    std::string("Invalid facet string attribute ") + name);
  std::string result;
  if (H5Tis_variable_str(type.id) > 0) {
    char* value = nullptr;
    require(H5Aread(item.id, type.id, &value) >= 0,
      std::string("Unable to read facet attribute ") + name);
    if (value) { result = value; H5free_memory(value); }
  } else {
    const auto size = H5Tget_size(type.id);
    require(size > 0 && size <= 1'000'000,
      std::string("Invalid facet attribute length ") + name);
    std::vector<char> value(size + 1, '\0');
    require(H5Aread(item.id, type.id, value.data()) >= 0,
      std::string("Unable to read facet attribute ") + name);
    result = value.data();
  }
  return result;
}

std::vector<double> vertices(hid_t group, std::size_t& count)
{
  Handle dataset {H5Dopen2(group, "triangle_vertices", H5P_DEFAULT), H5Dclose};
  require(dataset.id >= 0, "Missing facet triangle_vertices dataset");
  Handle space {H5Dget_space(dataset.id), H5Sclose};
  require(space.id >= 0 && H5Sget_simple_extent_ndims(space.id) == 3,
    "Facet triangle_vertices must have rank 3");
  hsize_t dimensions[3] {};
  require(H5Sget_simple_extent_dims(space.id, dimensions, nullptr) == 3
      && dimensions[0] > 0 && dimensions[0] <= 10'000'000
      && dimensions[1] == 3 && dimensions[2] == 3,
    "Facet triangle_vertices must have shape (n,3,3) with finite n");
  Handle type {H5Dget_type(dataset.id), H5Tclose};
  require(type.id >= 0 && H5Tget_class(type.id) == H5T_FLOAT
      && H5Tget_size(type.id) == sizeof(double),
    "Facet triangle_vertices must be binary64");
  count = static_cast<std::size_t>(dimensions[0]);
  std::vector<double> result(count * 9);
  require(H5Dread(dataset.id, H5T_NATIVE_DOUBLE, H5S_ALL, H5S_ALL,
            H5P_DEFAULT, result.data()) >= 0,
    "Unable to read facet triangle_vertices");
  for (const double value : result)
    require(std::isfinite(value), "Facet vertices must be finite");
  return result;
}

std::vector<std::int32_t> components(hid_t group, std::size_t count)
{
  Handle dataset {H5Dopen2(group, "component_ids", H5P_DEFAULT), H5Dclose};
  require(dataset.id >= 0, "Missing facet component_ids dataset");
  Handle space {H5Dget_space(dataset.id), H5Sclose};
  require(space.id >= 0 && H5Sget_simple_extent_ndims(space.id) == 1,
    "Facet component_ids must have rank 1");
  hsize_t dimensions[1] {};
  require(H5Sget_simple_extent_dims(space.id, dimensions, nullptr) == 1
      && dimensions[0] == count,
    "Facet component_ids must match triangle count");
  Handle type {H5Dget_type(dataset.id), H5Tclose};
  require(type.id >= 0 && H5Tget_class(type.id) == H5T_INTEGER
      && H5Tget_size(type.id) == sizeof(std::int32_t)
      && H5Tget_sign(type.id) == H5T_SGN_2,
    "Facet component_ids must be signed int32");
  std::vector<std::int32_t> result(count);
  require(H5Dread(dataset.id, H5T_NATIVE_INT32, H5S_ALL, H5S_ALL,
            H5P_DEFAULT, result.data()) >= 0,
    "Unable to read facet component_ids");
  for (const auto value : result)
    require(value > 0, "Facet component IDs must be positive");
  return result;
}

void update_little_endian(Sha256& digest, double value)
{
  std::uint64_t bits = 0;
  std::memcpy(&bits, &value, sizeof(bits));
  std::array<std::uint8_t, 8> bytes {};
  for (std::size_t i = 0; i < bytes.size(); ++i)
    bytes[i] = static_cast<std::uint8_t>(bits >> (8u * i));
  digest.update(bytes.data(), bytes.size());
}

void update_little_endian(Sha256& digest, std::int32_t value)
{
  const auto bits = static_cast<std::uint32_t>(value);
  std::array<std::uint8_t, 4> bytes {};
  for (std::size_t i = 0; i < bytes.size(); ++i)
    bytes[i] = static_cast<std::uint8_t>(bits >> (8u * i));
  digest.update(bytes.data(), bytes.size());
}

} // namespace

std::string facet_payload_content_id(const FacetPayloadData& data)
{
  require(!data.canonical_metadata_json.empty(),
    "Facet canonical metadata is required");
  Sha256 digest;
  digest.update(data.canonical_metadata_json.data(),
    data.canonical_metadata_json.size());
  for (const auto& triangle : data.triangles) {
    for (const auto& vertex : {triangle.a, triangle.b, triangle.c}) {
      update_little_endian(digest, vertex.x);
      update_little_endian(digest, vertex.y);
      update_little_endian(digest, vertex.z);
    }
  }
  for (const auto& triangle : data.triangles)
    update_little_endian(digest, static_cast<std::int32_t>(triangle.component_id));
  return "sha256:" + digest.hex_digest();
}

FacetPayloadData read_facet_payload_hdf5(
  const std::string& filename, const std::string& dataset,
  const std::string& expected_content_id)
{
  Handle file {H5Fopen(filename.c_str(), H5F_ACC_RDONLY, H5P_DEFAULT), H5Fclose};
  require(file.id >= 0, "Unable to open facet payload file " + filename);
  Handle group {H5Gopen2(file.id, dataset.c_str(), H5P_DEFAULT), H5Gclose};
  require(group.id >= 0, "Unable to open facet payload group " + dataset);
  require(attribute(group.id, "units") == "cm", "Facet units must be cm");
  FacetPayloadData result;
  result.canonical_metadata_json = attribute(group.id, "canonical_metadata_json");
  result.content_id = attribute(group.id, "content_id");
  require(expected_content_id.empty() || expected_content_id == result.content_id,
    "Facet content_id mismatch");
  std::size_t count = 0;
  const auto coordinates = vertices(group.id, count);
  const auto ids = components(group.id, count);
  result.triangles.reserve(count);
  for (std::size_t i = 0; i < count; ++i) {
    const std::size_t p = 9 * i;
    result.triangles.push_back({
      {coordinates[p], coordinates[p + 1], coordinates[p + 2]},
      {coordinates[p + 3], coordinates[p + 4], coordinates[p + 5]},
      {coordinates[p + 6], coordinates[p + 7], coordinates[p + 8]},
      static_cast<int>(ids[i])});
  }
  require(result.content_id.size() == 71
      && result.content_id.rfind("sha256:", 0) == 0,
    "Facet content_id must be a canonical SHA-256 ID");
  require(facet_payload_content_id(result) == result.content_id,
    "Facet canonical payload SHA-256 does not verify");
  return result;
}

} // namespace stellarcsg

#endif
