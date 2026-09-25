# Test doubles, not an OpenMC runtime

Only the opt-in isolation runner adds this directory to its include path.
The production C++ adapters, collection implementation, their public adapter
headers, and root/vector result types are compiled unchanged. Member geometry
is an analytic sphere double; this is not an admitted swept-spline payload.
OpenMC's base surface, XML-node interface, fatal-error routine, coefficient
reader, fmt, and counters are doubles. The HDF5 write double calls the installed
HDF5 C library, so output files are real HDF5, but production I/O linkage is NOT
qualified. No transport, tally scoring, native ZTorus, or solver is simulated.
