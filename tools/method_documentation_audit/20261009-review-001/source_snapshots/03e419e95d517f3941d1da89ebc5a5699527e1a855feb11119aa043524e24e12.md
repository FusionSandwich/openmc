# Final tally delta review 005

Source decision: **ACCEPT_SOURCE**, scoped to filter.py hash
3a5371909d919f278369a1ce47719192ea7646cf18e08df48c6717a1f9063651.
Final exact-byte test acceptance is **PASS_TARGETED**: the requested retained
stdout now reports 13 passed in 1.16s, with owner-recorded zero exit and unchanged
pre/post hashes. I independently rehashed stdout, final source/tests and library.
See TALLY_RECEIPT_005.json. This supersedes the initial pending state.
This reviewer does not edit the owner source/tests, and acceptance is invalid
if these input bytes change without reviewing their delta.

Final dedicated tests hash
3d508ad8950f1362facf0a9defa60a49b4a9de2ca7cd53a803e5e9cde977dda5.
The previously passing test file hash was
9366b910b015abfd55ac6f856b333fb73cf0ce5052643ad9c9bfac0312e16dcc.
The Linux pass is reported as 13 tests in 1.69s under the correct explicit
checkout and library f301f7a7..., but only its append-only narrative receipt
was initially available. The later handoff explicitly says bins.shape was
added to source after that run. Assertions that unequal objects have unequal
hashes were also removed; that weaker assertion-only test change is sound and
does not require retesting by itself. The post-run source refinement is the
specific reason for the final-byte receipt request sent to the existing owner,
not a blanket retest or inferred permission requirement.

## Independent source/consumer result

Equality and hash use the same exact class, mesh.id, bins.shape/values and
translation/rotation structural values. Shape retention restores the base
Filter's np.array_equal shape distinction and prevents flatten-only collisions
from becoming equality. Numeric tuples make signed zero and equal int/float
representations consistent with Python hash equality. Unequal objects may
legitimately have equal hashes. Exact type short-circuits unrelated classes.

MeshMaterialFilter's valid bins setter stores integer (element,material-ID)
pairs; its own hash now delegates to the common key, retaining its bins and
transform identity. Missing _rotation on material-filter initialization is
handled by getattr(..., None). MeshSurfaceFilter's surface-labeled bins and
MeshBornFilter's ordinary bins are inherited by the same structural key; true
subclasses remain distinct. A material-filter rotation interface is not newly
qualified by this base repair.

Tallies._create_filter_subelements uses a dictionary keyed by these filters and
rewrites duplicate IDs. With the repaired common identity, distinct transforms
and material bin lists cannot be collapsed because bins were ignored, while
equal filters share a hash. No C++ filter/scoring behavior or physical tally
normalization changed. Mutable keys must still not be changed while held in a
dict/set; the repair does not make mesh/filter data immutable.

Base HDF5 reader accepts finite flat 9/12 native rotation entries and preserves
the stored first nine as row-major matrix. The native writer stores the inverse
matrix first and optional original angles last. No recomputed-angle substitution
is made. Public transform setters reject nonfinite values/invalid shapes.

## Finite test coverage and limits

The final 13-test suite exercises actual Python package/XML behavior, signed-zero
and int/float MeshFilter equal hashes, valid MeshMaterialFilter unequal bins and
translations, MeshSurfaceFilter equal hashes/exact class distinction, distinct
mesh IDs, four transformed filter XML exports/roundtrip, and finite malformed/
nonfinite HDF5 and setter controls. The HDF5 cases are manually constructed
native-layout groups, not fresh native-generated statepoints. MeshBornFilter
has no dedicated new test; its unchanged inherited construction was inspected.

The material-bin inequality is asserted before translation mutation. In the
subsequent material XML test, both bins and translations differ; that XML case
alone would not isolate bins-only deduplication. The source key identity plus
the earlier valid bins-only inequality supplies the narrow conclusion. No claim
of exhaustive subclass, matrix/native transport or tiny-track scoring coverage.
Do not demand a broader suite merely to close this simple identity repair.

The final owner receipt binds final source and tests, the correct existing
runtime/package/library paths, captured stdout, reported zero exit, source-before/
after and the exclusive bounded lease. It reports one thread, 512 MiB virtual
memory and 60s timeout; the lease was released after exit. Its raw stdout warns
that OPENMC_CROSS_SECTIONS is absent; these Python/XML/HDF5 tests do not transport
particles or require nuclear data. This does not invalidate the targeted pass.
No new environment/acquisition/native build was performed. The reviewer did not
duplicate the test run or infer native transport acceptance from it.
