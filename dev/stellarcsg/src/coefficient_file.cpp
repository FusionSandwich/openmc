#include "stellarcsg/coefficient_file.hpp"

#ifdef STELLARCSG_HAS_HDF5

#include <hdf5.h>
#include <hdf5_hl.h>

#include <algorithm>
#include <array>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>

namespace stellarcsg {
namespace {

class H5Handle {
public:
  H5Handle() = default;
  H5Handle(hid_t id, herr_t (*closer)(hid_t)) : id_ {id}, closer_ {closer} {}
  H5Handle(const H5Handle&) = delete;
  H5Handle& operator=(const H5Handle&) = delete;
  H5Handle(H5Handle&& other) noexcept
    : id_ {other.id_}, closer_ {other.closer_}
  {
    other.id_ = -1;
  }
  ~H5Handle()
  {
    if (id_ >= 0 && closer_) closer_(id_);
  }
  [[nodiscard]] hid_t get() const noexcept { return id_; }
  [[nodiscard]] bool valid() const noexcept { return id_ >= 0; }

private:
  hid_t id_ {-1};
  herr_t (*closer_)(hid_t) {nullptr};
};

void require(bool condition, const std::string& message)
{
  if (!condition) throw std::runtime_error(message);
}


htri_t link_exists(hid_t location, const char* path) noexcept
{
  htri_t result = 0;
  H5E_BEGIN_TRY
  {
    result = H5Lexists(location, path, H5P_DEFAULT);
  }
  H5E_END_TRY
  return result;
}

std::string normalize_group_path(const std::string& input)
{
  require(!input.empty(), "HDF5 surface path cannot be empty");
  std::string result = input.front() == '/' ? input : "/" + input;
  while (result.size() > 1 && result.back() == '/') result.pop_back();
  return result;
}

hid_t ensure_group(hid_t file, const std::string& path)
{
  const std::string normalized = normalize_group_path(path);
  if (link_exists(file, normalized.c_str()) > 0) {
    return H5Gopen2(file, normalized.c_str(), H5P_DEFAULT);
  }

  std::string current;
  std::size_t start = 1;
  while (start <= normalized.size()) {
    const auto slash = normalized.find('/', start);
    const auto end = slash == std::string::npos ? normalized.size() : slash;
    current += "/" + normalized.substr(start, end - start);
    if (link_exists(file, current.c_str()) <= 0) {
      const H5Handle created {
        H5Gcreate2(file, current.c_str(), H5P_DEFAULT, H5P_DEFAULT, H5P_DEFAULT),
        H5Gclose};
      require(created.valid(), "Unable to create HDF5 group " + current);
    }
    if (slash == std::string::npos) break;
    start = slash + 1;
  }
  return H5Gopen2(file, normalized.c_str(), H5P_DEFAULT);
}

void write_string_attribute(hid_t object, const char* name,
  const std::string& value)
{
  require(H5LTset_attribute_string(object, ".", name, value.c_str()) >= 0,
    std::string("Unable to write HDF5 string attribute ") + name);
}

std::string read_string_attribute(hid_t object, const char* name,
  const std::string& fallback = {})
{
  if (H5Aexists(object, name) <= 0) return fallback;
  const H5Handle attribute {H5Aopen(object, name, H5P_DEFAULT), H5Aclose};
  require(attribute.valid(), std::string("Unable to open attribute ") + name);
  const H5Handle type {H5Aget_type(attribute.get()), H5Tclose};
  require(type.valid(), std::string("Unable to inspect attribute ") + name);
  if (H5Tis_variable_str(type.get()) > 0) {
    char* value = nullptr;
    require(H5Aread(attribute.get(), type.get(), &value) >= 0,
      std::string("Unable to read variable-length attribute ") + name);
    const std::string result = value ? std::string(value) : std::string();
    if (value) H5free_memory(value);
    return result;
  }

  const std::size_t size = H5Tget_size(type.get());
  std::vector<char> buffer(size + 1, '\0');
  require(H5Aread(attribute.get(), type.get(), buffer.data()) >= 0,
    std::string("Unable to read attribute ") + name);
  return std::string(buffer.data());
}

void write_vector(hid_t group, const char* name,
  const std::vector<double>& values)
{
  const hsize_t dims[1] {values.size()};
  require(H5LTmake_dataset_double(group, name, 1, dims, values.data()) >= 0,
    std::string("Unable to write dataset ") + name);
}

std::vector<double> read_vector(hid_t group, const char* name)
{
  int rank = 0;
  require(H5LTget_dataset_ndims(group, name, &rank) >= 0 && rank == 1,
    std::string("Expected one-dimensional dataset ") + name);
  hsize_t dims[1] {};
  H5T_class_t type_class;
  std::size_t type_size = 0;
  require(H5LTget_dataset_info(group, name, dims, &type_class, &type_size) >= 0,
    std::string("Unable to inspect dataset ") + name);
  std::vector<double> values(static_cast<std::size_t>(dims[0]));
  require(H5LTread_dataset_double(group, name, values.data()) >= 0,
    std::string("Unable to read dataset ") + name);
  return values;
}

} // namespace

void write_periodic_spline_surface_hdf5(const std::string& filename,
  const std::string& dataset, const PeriodicSplineSurfaceData& data,
  bool overwrite, CoefficientFileMode mode)
{
  const hid_t file_id = mode == CoefficientFileMode::truncate
    ? H5Fcreate(filename.c_str(), H5F_ACC_TRUNC, H5P_DEFAULT, H5P_DEFAULT)
    : (H5Fis_hdf5(filename.c_str()) > 0
        ? H5Fopen(filename.c_str(), H5F_ACC_RDWR, H5P_DEFAULT)
        : H5Fcreate(filename.c_str(), H5F_ACC_EXCL, H5P_DEFAULT, H5P_DEFAULT));
  const H5Handle file {file_id, H5Fclose};
  require(file.valid(), "Unable to open coefficient HDF5 file " + filename);

  const std::string path = normalize_group_path(dataset);
  if (link_exists(file.get(), path.c_str()) > 0) {
    require(overwrite, "HDF5 surface group already exists: " + path);
    require(H5Ldelete(file.get(), path.c_str(), H5P_DEFAULT) >= 0,
      "Unable to replace HDF5 surface group " + path);
  }
  const H5Handle group {ensure_group(file.get(), path), H5Gclose};
  require(group.valid(), "Unable to create HDF5 surface group " + path);

  const int schema[2] {data.schema_major, data.schema_minor};
  const hsize_t schema_dims[1] {2};
  require(H5LTmake_dataset_int(group.get(), "schema_version", 1,
    schema_dims, schema) >= 0, "Unable to write schema_version");
  write_string_attribute(group.get(), "surface_type", "periodic-radial-bicubic");
  write_string_attribute(group.get(), "units", data.units);
  write_string_attribute(group.get(), "content_id", data.content_id);
  require(H5LTset_attribute_int(group.get(), ".", "n_field_periods",
    &data.n_field_periods, 1) >= 0, "Unable to write n_field_periods");
  require(H5LTset_attribute_double(group.get(), ".", "characteristic_length",
    &data.characteristic_length, 1) >= 0,
    "Unable to write characteristic_length");
  require(H5LTset_attribute_double(group.get(), ".",
    "coordinate_singularity_tolerance",
    &data.coordinate_singularity_tolerance, 1) >= 0,
    "Unable to write coordinate_singularity_tolerance");

  write_vector(group.get(), "axis_r_coefficients", data.axis_r_coefficients);
  write_vector(group.get(), "axis_z_coefficients", data.axis_z_coefficients);
  const hsize_t radius_dims[2] {data.n_theta, data.n_phi};
  require(H5LTmake_dataset_double(group.get(), "radius_coefficients", 2,
    radius_dims, data.radius_coefficients.data()) >= 0,
    "Unable to write radius_coefficients");
}

PeriodicSplineSurfaceData read_periodic_spline_surface_hdf5(
  const std::string& filename, const std::string& dataset,
  const std::string& expected_content_id)
{
  const H5Handle file {
    H5Fopen(filename.c_str(), H5F_ACC_RDONLY, H5P_DEFAULT), H5Fclose};
  require(file.valid(), "Unable to open coefficient HDF5 file " + filename);
  const std::string path = normalize_group_path(dataset);
  const H5Handle group {H5Gopen2(file.get(), path.c_str(), H5P_DEFAULT), H5Gclose};
  require(group.valid(), "Unable to open HDF5 surface group " + path);

  PeriodicSplineSurfaceData data;
  int schema[2] {};
  require(H5LTread_dataset_int(group.get(), "schema_version", schema) >= 0,
    "Unable to read schema_version");
  data.schema_major = schema[0];
  data.schema_minor = schema[1];
  data.units = read_string_attribute(group.get(), "units", "cm");
  data.content_id = read_string_attribute(group.get(), "content_id");
  if (!expected_content_id.empty() && data.content_id != expected_content_id) {
    throw std::runtime_error("Coefficient content_id mismatch: expected '"
      + expected_content_id + "' but file contains '" + data.content_id + "'");
  }
  require(H5LTget_attribute_int(group.get(), ".", "n_field_periods",
    &data.n_field_periods) >= 0, "Unable to read n_field_periods");
  require(H5LTget_attribute_double(group.get(), ".", "characteristic_length",
    &data.characteristic_length) >= 0,
    "Unable to read characteristic_length");
  if (H5Aexists(group.get(), "coordinate_singularity_tolerance") > 0) {
    require(H5LTget_attribute_double(group.get(), ".",
      "coordinate_singularity_tolerance",
      &data.coordinate_singularity_tolerance) >= 0,
      "Unable to read coordinate_singularity_tolerance");
  }
  data.axis_r_coefficients = read_vector(group.get(), "axis_r_coefficients");
  data.axis_z_coefficients = read_vector(group.get(), "axis_z_coefficients");

  int rank = 0;
  require(H5LTget_dataset_ndims(group.get(), "radius_coefficients", &rank) >= 0
      && rank == 2,
    "radius_coefficients must be a two-dimensional dataset");
  hsize_t dims[2] {};
  H5T_class_t type_class;
  std::size_t type_size = 0;
  require(H5LTget_dataset_info(group.get(), "radius_coefficients", dims,
    &type_class, &type_size) >= 0,
    "Unable to inspect radius_coefficients");
  data.n_theta = static_cast<std::size_t>(dims[0]);
  data.n_phi = static_cast<std::size_t>(dims[1]);
  data.radius_coefficients.resize(data.n_theta * data.n_phi);
  require(H5LTread_dataset_double(group.get(), "radius_coefficients",
    data.radius_coefficients.data()) >= 0,
    "Unable to read radius_coefficients");
  return data;
}

} // namespace stellarcsg

#endif
