"""Bounded negative controls against the actual native shared-coil wrapper.

Run only after the coordinator releases the explicitly selected native build.
The probe links that build's libopenmc, not the standalone reference kernel.
Expected rejections occur before transport (one history maximum if rejection is
broken). All inputs, commands, failures, and hashes remain
in a newly created output directory; the successful reference is read only.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET

import h5py


PROBE = r'''
#include "openmc/surface_swept_spline.h"
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>

int main(int argc, char** argv) {
  if (argc != 4) return 90;
  pugi::xml_document document;
  if (!document.load_file(argv[1])) return 91;
  pugi::xml_node nodes[2];
  for (auto node : document.child("geometry").children("surface")) {
    const int id = node.attribute("id").as_int();
    if (id == 501) nodes[0] = node;
    if (id == 502) nodes[1] = node;
  }
  if (!nodes[0] || !nodes[1]) return 92;
  if (std::string(argv[2]) == "missing-association") {
    openmc::SurfaceSweptSpline member(nodes[0]);
    std::cout << "ACTIVE_NATIVE_WRAPPER surface=501 coincident=true\n" << std::flush;
    const double result = member.distance({100., 0., 0.}, {1., 0., 0.}, true);
    std::cout << "UNEXPECTED_ORDINARY_RETURN " << result << '\n';
    return 93;
  }
  std::ifstream input(argv[3]);
  openmc::Position position[2];
  openmc::Direction direction[2];
  for (int i = 0; i != 2; ++i)
    if (!(input >> position[i].x >> position[i].y >> position[i].z
          >> direction[i].x >> direction[i].y >> direction[i].z)) return 94;
  std::cout << std::setprecision(17);
  for (int lifetime = 0; lifetime != 3; ++lifetime) {
    openmc::SurfaceSweptSpline first(nodes[0]), second(nodes[1]);
    openmc::SurfaceSweptSpline* members[2] = {&first, &second};
    for (int q = 0; q != 2; ++q) {
      const double own = members[q]->distance(position[q], direction[q], false);
      const double other = members[1-q]->distance(position[q], direction[q], false);
      const double other_again = members[1-q]->distance(position[q], direction[q], false);
      const double own_again = members[q]->distance(position[q], direction[q], false);
      if (!std::isfinite(own) || !(own > 0.) || !(own < other)
          || own != own_again || other != other_again) return 95;
      std::cout << "MEMBER_CACHE lifetime=" << lifetime << " member=" << q+1
        << " own=" << own << " other=" << other << " PASS\n";
    }
  }
  std::cout << "LIFETIME_MEMBER_CACHE_PASS\n";
}
'''


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(command, directory, log_name, timeout=90):
    started = time.perf_counter()
    with (directory / log_name).open('x') as stream:
        try:
            result = subprocess.run(command, cwd=directory, stdout=stream,
                                    stderr=subprocess.STDOUT, timeout=timeout,
                                    env={**os.environ, 'OMP_NUM_THREADS': '1',
                                         'OPENBLAS_NUM_THREADS': '1'})
            code = result.returncode
        except subprocess.TimeoutExpired:
            code = None
    return dict(command=[str(x) for x in command], returncode=code,
                wall_seconds=time.perf_counter()-started, log=log_name)


def main():
    parser = argparse.ArgumentParser(__doc__)
    for name in ('source-root', 'build-root', 'executable', 'reference', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--source-sha', required=True)
    args = parser.parse_args()
    root, build, executable, reference, out = (
        getattr(args, name).resolve() for name in
        ('source_root', 'build_root', 'executable', 'reference', 'output'))
    assert executable == build / 'bin/openmc', 'Executable must belong to declared build'
    library = build / 'lib/libopenmc.so'
    assert library.is_file() and executable.is_file()
    # Bind both executable and tiny wrapper probe to this exact native library.
    # This modifies only the qualification subprocess environment.
    os.environ['LD_LIBRARY_PATH'] = str(library.parent)
    out.mkdir(parents=True, exist_ok=False)
    names = ['geometry.xml', 'materials.xml', 'settings.xml', 'tallies.xml',
             'coils.h5', 'plasma.h5', 'synthetic_mg.h5', 'source_bank.h5']
    before = {name: digest(reference / name) for name in names}
    receipt = dict(source_sha=args.source_sha, source_root=str(root),
                   executable_sha256=digest(executable), library_sha256=digest(library),
                   script_sha256=digest(__file__), reference=str(reference),
                   reference_sha256=before, histories_executed=None, controls={})
    receipt_path = out / 'receipt.json'

    def save():
        receipt_path.write_text(json.dumps(receipt, indent=2)+'\n')

    save()
    receipt['executable_linkage'] = run(['/usr/bin/ldd', str(executable)], out,
                                       'executable-ldd.log')
    linkage = (out / 'executable-ldd.log').read_text()
    assert 'libopenmc.so => '+str(library) in linkage, 'Unbound native executable library'
    save()
    negative = out / 'permuted-coil-ids'
    negative.mkdir()
    for name in ('geometry.xml', 'materials.xml', 'settings.xml', 'tallies.xml', 'coils.h5'):
        shutil.copyfile(reference / name, negative / name)
    # Swap whole groups, preserving each group's valid content hash and coil_id.
    # This isolates suffix/identity validation from ordinary hash-corruption checks.
    with h5py.File(negative / 'coils.h5', 'r+') as handle:
        handle.move('/coils/coil_001', '/coils/temporary')
        handle.move('/coils/coil_002', '/coils/coil_001')
        handle.move('/coils/temporary', '/coils/coil_002')
    geometry = ET.parse(negative / 'geometry.xml')
    for surface in geometry.findall('surface'):
        if surface.get('type') == 'swept-spline':
            surface.set('data_file', str(negative / 'coils.h5'))
    geometry.write(negative / 'geometry.xml', encoding='utf-8', xml_declaration=True)
    settings = ET.parse(negative / 'settings.xml')
    settings.find('particles').text = '1'
    settings.find('batches').text = '1'
    track = settings.find('track')
    if track is not None:
        settings.getroot().remove(track)
    settings.write(negative / 'settings.xml', encoding='utf-8', xml_declaration=True)
    item = run([str(executable), '-s', '1'], negative, 'native.log')
    log = ' '.join((negative / 'native.log').read_text().split())
    item['state'] = 'PASS' if (item['returncode'] not in (None, 0)
        and 'Shared collection coil_id must match its declared dataset suffix' in log) else 'FAIL'
    item['mutated_payload_sha256'] = digest(negative / 'coils.h5')
    receipt['controls']['permuted_coil_ids'] = item
    if item['state'] == 'PASS':
        receipt['histories_executed'] = 0
    save()

    probe = out / 'native-wrapper-probe'
    probe.mkdir()
    (probe / 'probe.cpp').write_text(PROBE)
    with h5py.File(reference / 'source_bank.h5', 'r') as handle:
        bank = handle['source_bank'][:]
    rows = []
    for sign in (1, -1):
        particle = next(p for p in bank if sign*float(p['r']['x']) > 15.)
        rows.append([float(particle[field][axis]) for field in ('r', 'u') for axis in ('x', 'y', 'z')])
    (probe / 'queries.txt').write_text('\n'.join(' '.join(map(repr, row)) for row in rows)+'\n')
    command = ['/usr/bin/g++', '-std=c++17', '-O2', '-DOPENMC_EXPERIMENTAL_STELLARCSG',
               '-I'+str(root / 'include'), '-I'+str(root / 'dev/stellarcsg/include'),
               '-I'+str(build / 'include'), '-I/usr/include/hdf5/serial',
               '-I'+str(root / 'vendor/pugixml/src'), '-I'+str(root / 'vendor/fmt/include'),
               str(probe / 'probe.cpp'), str(library), '-Wl,-rpath,'+str(library.parent),
               '-o', str(probe / 'probe')]
    compilation = run(command, probe, 'compile.log')
    receipt['probe_compile'] = compilation
    save()
    if compilation['returncode'] == 0:
        receipt['probe_sha256'] = digest(probe / 'probe')
        for mode in ('missing-association', 'lifetime-member-cache'):
            item = run([str(probe / 'probe'), str(reference / 'geometry.xml'), mode,
                        str(probe / 'queries.txt')], probe, mode+'.log')
            log = ' '.join((probe / (mode+'.log')).read_text().split())
            if mode == 'missing-association':
                passed = (item['returncode'] not in (None, 0)
                    and 'ACTIVE_NATIVE_WRAPPER' in log
                    and 'Unresolved swept-spline distance on surface 501' in log
                    and 'coincidence assertion has no origin-associated root' in log
                    and 'UNEXPECTED_ORDINARY_RETURN' not in log)
            else:
                passed = item['returncode'] == 0 and log.count('MEMBER_CACHE lifetime=') == 6
                passed = passed and 'LIFETIME_MEMBER_CACHE_PASS' in log
            item['state'] = 'PASS' if passed else 'FAIL'
            receipt['controls'][mode] = item
            save()
    else:
        for mode in ('missing-association', 'lifetime-member-cache'):
            receipt['controls'][mode] = {'state': 'BLOCKED', 'reason': 'native probe compile failed'}
    after = {name: digest(reference / name) for name in names}
    receipt['reference_preserved'] = before == after
    receipt['executable_sha256_after'] = digest(executable)
    receipt['library_sha256_after'] = digest(library)
    receipt['binary_preserved'] = (
        receipt['executable_sha256'] == receipt['executable_sha256_after']
        and receipt['library_sha256'] == receipt['library_sha256_after'])
    receipt['state'] = 'PASS' if (before == after and receipt['binary_preserved'] and
        all(item['state'] == 'PASS' for item in receipt['controls'].values())) else 'FAIL'
    save()
    print(json.dumps(receipt, indent=2))
    return 0 if receipt['state'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
