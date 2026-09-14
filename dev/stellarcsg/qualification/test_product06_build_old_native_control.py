from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("product06_build_old_native_control.py")
SPEC = importlib.util.spec_from_file_location("product06_old", SCRIPT)
control = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(control)


def test_replaces_exactly_one_preserved_compile_and_link_object(tmp_path, monkeypatch) -> None:
    build, source = tmp_path / "build", tmp_path / "old" / "compiled_swept_surface.cpp"
    build.mkdir()
    source.parent.mkdir()
    source.write_text("old source")
    database_source = tmp_path / "recovered" / "dev" / "stellarcsg" / "src" / "compiled_swept_surface.cpp"
    database_source.parent.mkdir(parents=True)
    database_source.write_text("new source")
    original = build / "CMakeFiles/openmc.dir/compiled_swept_surface.cpp.o"
    original.parent.mkdir(parents=True)
    original.write_text("object")
    (build / "compile_commands.json").write_text(json.dumps([{
        "file": str(database_source), "command": f"c++ -c \"{database_source}\" -o CMakeFiles/openmc.dir/compiled_swept_surface.cpp.o"}]))
    replacement = tmp_path / "replacement.o"
    compile, old_object = control.replace_compile_command(build, source, replacement)
    assert old_object == original.resolve()
    assert compile[compile.index("-c") + 1] == str(source.resolve())
    assert compile[compile.index("-o") + 1] == str(replacement)
    source_library = build / "lib" / "libopenmc.so"
    source_library.parent.mkdir()
    source_library.write_text("base library")
    copied_library = tmp_path / "source" / "openmc" / "lib" / "libopenmc.so"
    command = (f": && c++ -Wl,--dependency-file=CMakeFiles/libopenmc.dir/link.d -shared -o lib/libopenmc.so "
               f"{original.relative_to(build).as_posix()} -Wl,-soname,libopenmc.so && cd {build.as_posix()} && "
               f"/usr/bin/cmake -E copy {source_library.as_posix()} {copied_library.as_posix()}")
    prerequisite = ": && c++ -c unrelated.cpp -o CMakeFiles/unrelated.o && :"
    monkeypatch.setattr(control.subprocess, "run", lambda *args, **kwargs: type("Run", (), {"returncode": 0, "stdout": prerequisite + "\n" + command + "\n", "stderr": ""})())
    linked = control.link_tokens(build, original, replacement, tmp_path / "libopenmc.so")
    assert str(replacement) in linked
    assert str(tmp_path / "libopenmc.so") in linked
    assert "-Wl,-soname,libopenmc.so" in linked
    assert any(token.startswith("-Wl,--dependency-file=") and "link.d" in token for token in linked)
    assert "copy" not in linked
