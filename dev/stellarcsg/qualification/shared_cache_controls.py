"""Bounded actual-native cache controls; all output goes to a new directory.

Forty distinct cheap bbox-miss rays and exact native counter deltas exercise
32-slot replacement without forty expensive GMP root solves. Classification
replacement is reviewed statically; two real inside signs are checked here.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess

import h5py
from shared_native_negative_controls import digest, run

PROBE = r'''
#include "openmc/surface_swept_spline.h"
#include <array>
#include <atomic>
#include <cmath>
#include <fstream>
#include <iostream>
#include <limits>
#include <string>
#include <thread>
#include <vector>

int main(int argc,char** argv) {
  if(argc!=4) return 90;
  pugi::xml_document xml;
  if(!xml.load_file(argv[1])) return 91;
  pugi::xml_node nodes[2];
  for(auto n:xml.child("geometry").children("surface")) {
    if(n.attribute("id").as_int()==501) nodes[0]=n;
    if(n.attribute("id").as_int()==502) nodes[1]=n;
  }
  if(!nodes[0]||!nodes[1]) return 92;
  openmc::SurfaceSweptSpline first(nodes[0]),second(nodes[1]);
  openmc::SurfaceSweptSpline* member[2]={&first,&second};
  const std::string mode=argv[2];
  if(mode=="coincidence-key") {
    const double cold=first.distance({100,0,0},{1,0,0},false);
    std::cout<<"WARM_FALSE "<<cold<<'\n'<<std::flush;
    const double unexpected=first.distance({100,0,0},{1,0,0},true);
    std::cout<<"UNEXPECTED_ORDINARY_RETURN "<<unexpected<<'\n'; return 93;
  }
  if(mode=="ring1"||mode=="ring2") {
    std::atomic<int> failures{0};
    const auto task=[&] {
      std::array<openmc::Position,40> r;
      std::array<openmc::Direction,40> u;
      for(int i=0;i<40;++i) {
        r[i]={100,0,0}; u[i]={1,0,0};
        if(i<20) for(int j=0;j<i+1;++j) r[i].x=std::nextafter(r[i].x,INFINITY);
        else for(int j=0;j<i-19;++j) u[i].x=std::nextafter(u[i].x,INFINITY);
      }
      std::array<double,40> cold;
      for(int i=0;i<40;++i) {
        cold[i]=first.distance(r[i],u[i],false);
        if(cold[i]<1e100||second.distance(r[i],u[i],false)!=cold[i]) ++failures;
      }
      for(int i=39;i>=0;--i) {
        if(second.distance(r[i],u[i],false)!=cold[i]
          ||first.distance(r[i],u[i],false)!=cold[i]) ++failures;
      }
    };
    const int count=mode=="ring2"?2:1;
    std::vector<std::thread> threads;
    for(int i=0;i<count;++i) threads.emplace_back(task);
    for(auto& t:threads) t.join();
    if(failures) return 94;
    std::cout<<"RING_PASS threads="<<count<<" distinct_queries=40\n";
    return 0;
  }
  std::ifstream input(argv[3]);
  openmc::Position p[2]; openmc::Direction u[2];
  for(int i=0;i<2;++i)
    if(!(input>>p[i].x>>p[i].y>>p[i].z>>u[i].x>>u[i].y>>u[i].z)) return 95;
  if(mode=="coincident-member-key") {
    const double entry=first.distance(p[0],u[0],false);
    const auto crossing=p[0]+entry*u[0];
    const double exit=first.distance(crossing,u[0],true);
    if(!(exit>.1&&exit<1.)) return 103;
    std::cout<<"WARM_COINCIDENT_MEMBER_A "<<exit<<'\n'<<std::flush;
    const double unexpected=second.distance(crossing,u[0],true);
    std::cout<<"UNEXPECTED_ORDINARY_RETURN "<<unexpected<<'\n'; return 104;
  }
  double hit[2];
  for(int i=0;i<2;++i) {
    hit[i]=member[i]->distance(p[i],u[i],false);
    if(!(hit[i]>.5&&hit[i]<1.5)) return 96;
    if(member[1-i]->distance(p[i],u[i],false)<1e100) return 97;
    if(member[i]->distance(p[i],u[i],false)!=hit[i]) return 98;
    const auto inside=p[i]+(hit[i]+.1)*u[i];
    const double sign=member[i]->evaluate(inside);
    if(!(sign<0)||!(member[1-i]->evaluate(inside)>0)
      ||member[i]->evaluate(inside)!=sign) return 99;
  }
  // Reuse the same payload filename but form a different immutable context:
  // local member index zero now denotes coil2, while the old context survives.
  pugi::xml_document changed;
  auto node=changed.append_copy(nodes[0]);
  node.attribute("id").set_value(503);
  node.attribute("dataset_start").set_value(2);
  node.attribute("dataset_count").set_value(1);
  node.attribute("member_id").set_value(2);
  for(int lifetime=0;lifetime<2;++lifetime) {
    openmc::SurfaceSweptSpline different(node);
    if(different.distance(p[0],u[0],false)<1e100) return 100;
    if(first.distance(p[0],u[0],false)!=hit[0]) return 101;
    if(!(different.evaluate(p[0]+(hit[0]+.1)*u[0])>0)) return 102;
  }
  std::cout<<"REAL_MEMBER_CONTEXT_PASS hits=2 inside_signs=2 lifetimes=2\n";
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source-root', 'build-root', 'reference', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    source, build, reference, out = [getattr(args, name).resolve() for name in
                                    ('source_root', 'build_root', 'reference', 'output')]
    out.mkdir(parents=True, exist_ok=False)
    library = build/'lib/libopenmc.so'
    executable = build/'bin/openmc'
    os.environ.update(LD_LIBRARY_PATH=str(library.parent), STELLARCSG_REPORT_SHARED='1')
    bound = [library, executable, reference/'geometry.xml', reference/'coils.h5',
             reference/'source_bank.h5']
    before = {str(p): digest(p) for p in bound}
    # Host-created worktrees contain a Windows absolute gitdir pointer. Resolve
    # that known mount mapping explicitly; never rewrite the worktree metadata.
    git_dir = source/'.git'
    if git_dir.is_file():
        pointer = git_dir.read_text().strip().removeprefix('gitdir: ')
        if len(pointer) > 2 and pointer[1] == ':':
            pointer = '/mnt/'+pointer[0].lower()+pointer[2:].replace('\\', '/')
        git_dir = Path(pointer)
        if not git_dir.is_absolute(): git_dir = source/git_dir
    receipt = {'source_head': subprocess.check_output(['/usr/bin/git', '--git-dir', str(git_dir),
                 'rev-parse', 'HEAD'], text=True).strip(),
               'wrapper_sha256': digest(source/'src/surface_swept_spline.cpp'),
               'script_sha256': digest(__file__), 'before_sha256': before, 'controls': {},
               'classification_eviction': 'NOT_RUN; reviewed statically; two actual inside signs tested'}
    (out/'probe.cpp').write_text(PROBE)
    with h5py.File(reference/'source_bank.h5') as h:
        bank = h['source_bank'][:]
    rows = []
    for sign in (1, -1):
        p = next(p for p in bank if sign*float(p['r']['x']) > 15)
        rows.append([float(p[f][a]) for f in ('r', 'u') for a in ('x', 'y', 'z')])
    (out/'queries.txt').write_text('\n'.join(' '.join(map(repr, r)) for r in rows)+'\n')
    command = ['/usr/bin/g++', '-std=c++17', '-O2', '-pthread', '-DOPENMC_EXPERIMENTAL_STELLARCSG',
               '-I'+str(source/'include'), '-I'+str(source/'dev/stellarcsg/include'),
               '-I'+str(build/'include'), '-I/usr/include/hdf5/serial',
               '-I'+str(source/'vendor/pugixml/src'), '-I'+str(source/'vendor/fmt/include'),
               str(out/'probe.cpp'), str(library), '-Wl,-rpath,'+str(library.parent),
               '-o', str(out/'probe')]
    receipt['compile'] = run(command, out, 'compile.log')
    if receipt['compile']['returncode'] != 0:
        receipt['state'] = 'BLOCKED'
    else:
        receipt['probe_sha256'] = digest(out/'probe')
        receipt['linkage'] = run(['/usr/bin/ldd', str(out/'probe')], out, 'ldd.log')
        assert 'libopenmc.so => '+str(library) in (out/'ldd.log').read_text()
        for mode in ('ring1', 'ring2', 'real-context', 'coincidence-key', 'coincident-member-key'):
            item = run([str(out/'probe'), str(reference/'geometry.xml'), mode,
                        str(out/'queries.txt')], out, mode+'.log', timeout=90)
            log = ' '.join((out/(mode+'.log')).read_text().split())
            if mode.startswith('ring'):
                n = int(mode[-1])
                counters = [(int(a), int(b)) for a, b in re.findall(
                    r'traversals=(\d+) cache_hits=(\d+)', log)]
                expected = (48*n, 112*n)
                passed = item['returncode'] == 0 and 'RING_PASS' in log
                passed = passed and len(counters) == 2 and all(c == expected for c in counters)
                item.update(counters=counters, expected_counters=expected)
            elif mode == 'real-context':
                passed = item['returncode'] == 0 and 'REAL_MEMBER_CONTEXT_PASS' in log
            else:
                marker = 'WARM_FALSE' if mode == 'coincidence-key' else 'WARM_COINCIDENT_MEMBER_A'
                passed = item['returncode'] not in (None, 0) and marker in log
                passed = passed and 'coincidence assertion has no origin-associated root' in log
                passed = passed and 'UNEXPECTED_ORDINARY_RETURN' not in log
            item['state'] = 'PASS' if passed else 'FAIL'
            receipt['controls'][mode] = item
        receipt['state'] = 'PASS' if all(c['state'] == 'PASS' for c in receipt['controls'].values()) else 'FAIL'
    receipt['after_sha256'] = {str(p): digest(p) for p in bound}
    receipt['inputs_and_binaries_preserved'] = before == receipt['after_sha256']
    if not receipt['inputs_and_binaries_preserved']: receipt['state'] = 'FAIL'
    (out/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt, indent=2))
    return 0 if receipt['state'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
