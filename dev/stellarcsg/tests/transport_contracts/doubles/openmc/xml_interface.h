#pragma once
#include "openmc/surface.h"
#include <algorithm>
#include <cctype>
namespace openmc {
inline bool check_for_node(const pugi::xml_node& n, const std::string& k) {
  return n.attrs.count(k)!=0;
}
inline std::string get_node_value(const pugi::xml_node& n,
  const std::string& k, bool lower=false, bool=true) {
  auto s=n.attrs.at(k);
  if (lower) std::transform(s.begin(),s.end(),s.begin(),
    [](unsigned char c){return static_cast<char>(std::tolower(c));});
  return s;
}
}
