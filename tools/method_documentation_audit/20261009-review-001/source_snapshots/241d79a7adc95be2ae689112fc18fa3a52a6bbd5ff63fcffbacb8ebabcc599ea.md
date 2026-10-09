# Stage 1 implementation checkpoint, October 1, 2026

**PURE_OPERATIONS_PASS_NATIVE_PATH_NOT_WIRED.** The exact arithmetic foundation
of the root-reviewed unit-axis-plane proposal is implemented and tested. It is
not a minimum-only/sense-only native patch and does not claim a functional
navigation repair. Native OpenMC default behavior and all retained baseline/
current binaries are unchanged. No native model initialization or transport
ran. No acquisition, environment change, SSH, staging, commit or branch change.

## Implemented files and scope

* [dyadic_axis_plane.hpp](../include/stellarcsg/dyadic_axis_plane.hpp) exposes
  exact binary64 differences, ordering, explicit nearest-even conversion,
  unit-axis ray/contact status, strict event-point plane side, incoming/outgoing
  side limits and local interval lengths.
* [dyadic_axis_plane.cpp](../src/dyadic_axis_plane.cpp) implements those operations
  with a fixed 33-word signed magnitude. It has no new dependency, heap allocation,
  global mutable state, long-double approximation or coincidence epsilon.
* [test_dyadic_axis_plane.cpp](../tests/test_dyadic_axis_plane.cpp) contains
  meaningful directed controls and a bit-pattern query interface for the
  independent differential.
* [P00_DYADIC_AXIS_ORACLE_20261001.py](../tests/P00_DYADIC_AXIS_ORACLE_20261001.py)
  uses Python stdlib Fraction to construct expected exact magnitudes and rounded
  bits. It admits one serial build/test phase, stops on first failure, preserves
  diagnostics and conservatively retains the lease if WSL terminal state is
  unknown. No successor campaign is scheduled or launched.
* [Dev CMakeLists.txt](../CMakeLists.txt) adds the source to the standalone
  reference library and a CTest target, with strict source FP options. Root
  OpenMC CMake and production native files were not changed. The standalone
  direct compilation was tested; the full CMake/CTest build was not executed.

## Arithmetic contract and independent checks

Every finite binary64 value is an integer multiple of 2^-1074. Decode a normal
value's 53-bit significand into these units with shift `exponent_field-1`;
subnormal significands use shift zero. The highest magnitude bit of a single
finite value is at most 2097. A difference of two opposite-signed finite values
is strictly below 2^2099, so 33 uint64 words (2112 bits) contain every supported
difference. Addition/subtraction propagate explicit carry/borrow; exact signs
and lexicographic magnitudes establish order, including negative parameters.

Rounding finds the highest bit and retains the leading 53 bits. Guard plus
sticky bits implement ties-to-even, including exponent carry. Subnormal output
is encoded directly. Overflow returns an explicit overflow status and infinity;
it must be rejected by a navigation caller, never used as a valid finite length.
No nonzero difference of finite binary64 coordinates can underflow below the
minimum subnormal because the exact unit itself is 2^-1074. This fact is
specific to these coordinate differences; it does not establish representability
of arbitrary rational facet contact separations.

For declared unit-axis rays, parameter ordering is exact coordinate-difference
ordering. Local interval length is formed from boundary coordinates directly,
not from two rounded absolute parameters. Strict probe sides likewise use
integer-backed coordinate differences. An exactly contacting transverse plane
uses the incoming/outgoing direction; a noncontacting near plane retains its
strict sign. A parallel coplanar plane remains coplanar/zero-side, not a resolved
point crossing. Nonfinite inputs, invalid axes and non-unit-axis direction codes
are rejected.

The event_coordinate argument must come from a certified contact in the same
ray/frame. These primitives do not create a ray epoch, validate cell ownership,
deduplicate a contact group, suppress consumed origins, handle transforms or
commit scores. A future caller must establish those conditions and inspect
status before using a parameter/side/rounded result. The default primitive
parameter in a MISS/COPLANAR status is not an actual zero-distance contact.

## Completed acceptance evidence

The [frozen plan](P00_DYADIC_AXIS_PLAN_20261001.md),
[fresh complete inventory](P00_DYADIC_AXIS_INVENTORY_20261001.json),
[source/input identities](p00-dyadic-axis-20261001-01/identities.json), and
[terminal receipt](p00-dyadic-axis-20261001-01/receipt.json) are retained.

* GNU14 C++17 build, warnings as errors, strict FP and UBSan/no recover:
  **exit 0**, no warning or sanitizer diagnostic, 22.11 seconds including WSL.
* Directed controls: **exit 0**, 0.625 seconds. They check gap48 order and the
  strict outside-A side at B exit, local 2^-48 length, all axes/directions,
  origin/behind/miss/coplanar statuses, true ties, signed zero, minimum subnormal,
  overflow, invalid inputs, adjacent-double boundaries with no interior point,
  and different exact contacts with identical rounded absolute parameters.
  Integer-backed nearest-even rounding passes all four floating rounding modes.
* Fraction differential: **5,520/5,520 rows agree**, exit 0, 0.625 seconds for
  the client. Of these, 5,386 are finite-input exact-magnitude/rounding cases
  (including overflow), and 134 correctly reject nonfinite inputs. The bank
  combines systematic extremes/halfway cases with 5,000 deterministic random
  bit pairs. Exact signed units, rounded bits, overflow and exactness flags all
  match. The script requires complete cardinality and rejects seven corrupted
  magnitude/sign/rounding/status/exactness/schema outputs.
* Total phase: **23.578 seconds**, below 180-second cap, one CPU/thread,
  1 GiB address-space bound for each WSL compiler/client. Final output size
  2,297,113 bytes, below 30 MiB. Shared lease released after terminal children;
  final check observed it absent. There is no successor run.

Compiled test executable SHA256:
`eca93fd2109114786d98caaf581fb4a30967ea27aff7406dfe72423f3224b4b8`.
The test runner verified all pinned source/input and retained-library hashes
again before success. Final separate library checks also match:
current `9bf312f3e556b586fec44b714f179b97fa8dd5a25a249951674b01174b49432d`,
baseline `546be4c8af7da69196d6b4408de7bfb9af6ac0ddb424a90205cd513b60c19b9a`.

Only the new dev CMake edit is an additional tracked modification from this
task. The pre-existing METHOD_MAP, chat provenance and equivalence research
modifications were preserved. No production native source was edited. Git
diff --check passes for the CMake edit (only the existing LF/CRLF advisory).

## Exact remaining implementation work

The arithmetic foundation is ready for independent root review. The complete
opt-in native unit-axis-plane contract still requires the following coupled
work, not a collection of independently enabled one-line fixes:

1. **Opt-in and scope validation:** validate one CSG universe/coordinate level,
   void fills, unit-axis rays, permitted plane boundaries, Boolean expressions
   and the supported flux/canonical-current filter configuration. Reject
   unsupported transforms/lattices, material/collision evaluators, coplanar
   contacts and unsupported BC/filter semantics explicitly. Default dispatch
   must remain identical when the path is off. Use an outer plane box for the
   fully supported fixture; a nonplanar enclosing primitive needs a separately
   proved exclusion bound before it participates in a local control.
2. **Event context:** anchor/epoch, exact parameter/contact-coordinate keys,
   complete equal-time group, strict noncontact sides and consumed origin keys.
   Never infer the group from equal rounded distances or distance tolerances.
   Store the canonical representative separately from the group driving
   navigation. Caller state should own bounded/preallocated group storage;
   avoid a new allocation per hot-path event.
3. **Region and successor lookup:** original and R|R paths need context-aware
   membership and virtual traversal, using the same exact side/parameter logic.
   A selected-token-only override plus legacy sense cannot repair gap48.
   Establish candidate completeness independently of warm neighbor lists and
   UniversePartitioner; a context-aware full supported-universe search is the
   safe first version. Validate source initialization near a plane too, not
   only post-crossing lookup. Do not discard later positive hits via plane
   residual, complex traversal or origin-coincidence bands.
4. **Particle advance/score transaction:** construct the certified event and
   outgoing owner before committing the affected advance where possible;
   advance each strictly positive exact local delta and score it in the current
   predecessor cell. At a true group apply outgoing sides once, update
   cell_last/current once and score the documented canonical current once.
   Preserve logical progress even when Cartesian storage or absolute rounded
   parameter is unchanged. No TINY_BIT nudge can silently cross a required
   interval. Expose terminal unsupported reasons/partial diagnostics honestly.
5. **Lifecycle/ABI integration:** reset context at source/restart/direction or
   frame changes; do not silently re-enter legacy membership inside an active
   unresolved cluster. BoundaryInfo/GeometryState are public C++ types. The
   current root CMake sets OPENMC_EXPERIMENTAL_STELLARCSG **PRIVATE**; adding
   conditional public-class layout under that private definition would make
   external clients disagree with the library. Choose an ABI-consistent
   context representation/feature definition and rebuild only a new isolated
   experimental library/client pair. Never link a changed layout to the frozen
   baseline/current libraries.
6. **Native acceptance:** independently compare forward/reverse, token/XML/lookup
   order, touching and identical planes, gap/overlap ladder, adjacent boundaries,
   rounded-equal absolute parameters, and masked virtual events. Require exact
   cell itinerary and all local flux/current bins, not merely the first surface
   or summed score. Complete both matched plane clients; the earlier baseline
   plane timeout remains incomplete. Pin the arithmetic rounding policy in
   each manifest. Root review precedes any claim that the opt-in path passes.

This native context/lookup/score/lifecycle integration crosses Cell/Region,
BoundaryInfo/GeometryState, Universe and Particle/filter interfaces. It was
left unwired deliberately at a reproducible arithmetic checkpoint so that an
incomplete minimum or sense fix cannot be mistaken for the functional repair.
No native source change or new native build is bundled into this passing test
phase. Root can independently review the decisive foundation evidence and then
continue the coupled implementation under the existing user authorization,
with a fresh inventory and separate bounded build/run admission. No new user
permission request is needed for that authorized work.

## Limits

Random/directed tests are finite evidence, not a universal verified-arithmetic
proof. The representation/rounding argument needs independent review. Full
CMake/CTest configuration was not exercised. Native successor ownership,
interval scores, contact-group canonical scoring and default-off integration
have not been implemented or tested. Facet rational predicates, periodic
wrapping, collisions/time/spatial evaluators, scientific input fidelity and
performance targets remain out of scope. **Publication acceptance stays open.**
