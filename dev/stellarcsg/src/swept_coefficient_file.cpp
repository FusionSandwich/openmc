#include "stellarcsg/swept_coefficient_file.hpp"

#ifdef STELLARCSG_HAS_HDF5

#include "stellarcsg/sha256.hpp"

#include <hdf5.h>
#include <hdf5_hl.h>

#include <array>
#include <cstdint>
#include <cstring>
#include <stdexcept>
#include <vector>

namespace stellarcsg {
namespace {

void require(bool condition, const std::string& message)
{
  if (!condition) throw std::runtime_error(message);
}

std::string attribute(hid_t group, const char* name)
{
  const hid_t attribute_id = H5Aopen(group, name, H5P_DEFAULT);
  require(attribute_id >= 0, std::string("Missing swept-spline attribute ") + name);
  const hid_t type = H5Aget_type(attribute_id);
  require(type >= 0, "Unable to inspect swept-spline string attribute");
  std::string result;
  if (H5Tis_variable_str(type) > 0) {
    char* value = nullptr;
    require(H5Aread(attribute_id, type, &value) >= 0,
      "Unable to read swept-spline string attribute");
    if (value) { result = value; H5free_memory(value); }
  } else {
    std::vector<char> value(H5Tget_size(type) + 1, '\0');
    require(H5Aread(attribute_id, type, value.data()) >= 0,
      "Unable to read swept-spline string attribute");
    result = value.data();
  }
  H5Tclose(type);
  H5Aclose(attribute_id);
  return result;
}

std::vector<double> vector_dataset(hid_t group, const char* name,
  int expected_rank, std::size_t& first_dimension)
{
  int rank = 0;
  require(H5LTget_dataset_ndims(group, name, &rank) >= 0
      && rank == expected_rank, std::string("Invalid swept dataset ") + name);
  hsize_t dimensions[2] {1, 1};
  H5T_class_t type;
  std::size_t size = 0;
  require(H5LTget_dataset_info(group, name, dimensions, &type, &size) >= 0,
    std::string("Unable to inspect swept dataset ") + name);
  if (expected_rank == 2) require(dimensions[1] == 3,
    std::string("Swept vector dataset must have shape (n,3): ") + name);
  first_dimension = static_cast<std::size_t>(dimensions[0]);
  std::vector<double> values(first_dimension
    * (expected_rank == 2 ? 3u : 1u));
  require(H5LTread_dataset_double(group, name, values.data()) >= 0,
    std::string("Unable to read swept dataset ") + name);
  return values;
}

void update_little_endian(Sha256& digest, const std::vector<double>& values)
{
  for (double value : values) {
    std::uint64_t bits = 0;
    std::memcpy(&bits, &value, sizeof(bits));
    std::array<std::uint8_t, 8> bytes {};
    for (std::size_t i = 0; i < bytes.size(); ++i)
      bytes[i] = static_cast<std::uint8_t>(bits >> (8u * i));
    digest.update(bytes.data(), bytes.size());
  }
}

} // namespace

std::string swept_spline_content_id(const SweptSplineSurfaceData& data)
{
  require(!data.canonical_metadata_json.empty(),
    "Swept-spline canonical metadata is required");
  Sha256 digest;
  digest.update(data.canonical_metadata_json.data(),
    data.canonical_metadata_json.size());
  update_little_endian(digest, data.centerline_coefficients);
  update_little_endian(digest, data.normal_coefficients);
  update_little_endian(digest, data.binormal_coefficients);
  update_little_endian(digest, data.major_radius_coefficients);
  update_little_endian(digest, data.minor_radius_coefficients);
  return "sha256:" + digest.hex_digest();
}

SweptSplineSurfaceData read_swept_spline_surface_hdf5(
  const std::string& filename, const std::string& dataset,
  const std::string& expected_content_id)
{
  const hid_t file = H5Fopen(filename.c_str(), H5F_ACC_RDONLY, H5P_DEFAULT);
  require(file >= 0, "Unable to open swept-spline coefficient file " + filename);
  const hid_t group = H5Gopen2(file, dataset.c_str(), H5P_DEFAULT);
  if (group < 0) { H5Fclose(file); throw std::runtime_error(
    "Unable to open swept-spline group " + dataset); }
  SweptSplineSurfaceData data;
  const auto surface_type = attribute(group, "surface_type");
  require(surface_type == "swept-elliptical-cubic",
    "Unsupported swept-spline surface_type " + surface_type);
  require(attribute(group, "units") == "cm", "Swept-spline units must be cm");
  data.content_id = attribute(group, "content_id");
  data.canonical_metadata_json = attribute(group, "canonical_metadata_json");
  require(expected_content_id.empty() || expected_content_id == data.content_id,
    "Swept-spline content_id mismatch");
  require(H5LTget_attribute_int(group, ".", "coil_id", &data.coil_id) >= 0,
    "Unable to read swept-spline coil_id");
  require(H5LTget_attribute_double(group, ".", "length_cm", &data.length) >= 0,
    "Unable to read swept-spline length");
  std::size_t count = 0;
  data.centerline_coefficients = vector_dataset(
    group, "centerline_coefficients", 2, count);
  data.sample_count = count;
  std::size_t other = 0;
  data.normal_coefficients = vector_dataset(group, "normal_coefficients", 2, other);
  require(other == count, "Swept normal coefficient count mismatch");
  data.binormal_coefficients = vector_dataset(group, "binormal_coefficients", 2, other);
  require(other == count, "Swept binormal coefficient count mismatch");
  data.major_radius_coefficients = vector_dataset(
    group, "major_radius_coefficients", 1, other);
  require(other == count, "Swept major radius count mismatch");
  data.minor_radius_coefficients = vector_dataset(
    group, "minor_radius_coefficients", 1, other);
  require(other == count, "Swept minor radius count mismatch");
  data.characteristic_length = data.length;
  H5Gclose(group);
  H5Fclose(file);
  require(data.content_id.rfind("sha256:", 0) != 0
      || swept_spline_content_id(data) == data.content_id,
    "Swept-spline canonical payload SHA-256 does not verify");
  return data;
}

} // namespace stellarcsg

#endif
