#pragma once
#include <iomanip>
#include <sstream>
#include <string>
namespace fmt {
inline std::string format(const std::string& pattern) { return pattern; }
template<class T, class... Rest>
std::string format(const std::string& pattern, const T& value, const Rest&... rest) {
  const auto p=pattern.find('{');
  const auto end=pattern.find('}',p);
  if(p==std::string::npos || end==std::string::npos) return pattern;
  std::ostringstream out;
  if(pattern.substr(p,end-p+1)=="{:03d}") out<<std::setfill('0')<<std::setw(3);
  out<<value;
  return pattern.substr(0,p)+out.str()+format(pattern.substr(end+1),rest...);
}
}
