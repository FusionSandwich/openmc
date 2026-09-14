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
    original = build / "CMakeFiles/openmc.dir/compiled_swept_surface.cpp.o"
    original.parent.mkdir(parents=True)
    original.write_text("object")
    (build / "compile_commands.json").write_text(json.dumps([{
        "file": str(source), "command": f"c++ -c \"{source}\" -o CMakeFiles/openmc.dir/compiled_swept_surface.cpp.o"}]))
    replacement = tmp_path / "replacement.o"
    compile, old_object = control.replace_compile_command(build, source, replacement)
    assert old_object == original.resolve()
    assert compile[compile.index("-c") + 1] == str(source.resolve())
    assert compile[compile.index("-o") + 1] == str(replacement)
    command = f": && c++ -shared -o lib/libopenmc.so {original.relative_to(build).as_posix()} -Wl,-soname,libopenmc.so && :"
    monkeypatch.setattr(control.subprocess, "run", lambda *args, **kwargs: type("Run", (), {"returncode": 0, "stdout": command + "\n", "stderr": ""})())
    linked = control.link_tokens(build, original, replacement, tmp_path / "libopenmc.so")
    assert str(replacement) in linked
    assert str(tmp_path / "libopenmc.so") in linked
    assert "-Wl,-soname,libopenmc.so" in linked
