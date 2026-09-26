#pragma once
#include <hdf5.h>
#include <stdexcept>
#include <string>
namespace openmc {
inline void write_string(hid_t group, const std::string& name,
  const std::string& value, bool) {
  const hid_t type=H5Tcopy(H5T_C_S1);
  const hid_t space=H5Screate(H5S_SCALAR);
  H5Tset_size(type, value.empty()?1:value.size());
  const hid_t dataset=H5Dcreate2(group,name.c_str(),type,space,
    H5P_DEFAULT,H5P_DEFAULT,H5P_DEFAULT);
  const auto rc=H5Dwrite(dataset,type,H5S_ALL,H5S_ALL,H5P_DEFAULT,value.c_str());
  H5Dclose(dataset); H5Sclose(space); H5Tclose(type);
  if (rc<0) throw std::runtime_error("test HDF5 write failed");
}
inline void write_dataset(hid_t group, const std::string& name, int value) {
  const hid_t space=H5Screate(H5S_SCALAR);
  const hid_t dataset=H5Dcreate2(group,name.c_str(),H5T_NATIVE_INT,space,
    H5P_DEFAULT,H5P_DEFAULT,H5P_DEFAULT);
  const auto rc=H5Dwrite(dataset,H5T_NATIVE_INT,H5S_ALL,H5S_ALL,H5P_DEFAULT,&value);
  H5Dclose(dataset); H5Sclose(space);
  if (rc<0) throw std::runtime_error("test HDF5 write failed");
}
}
