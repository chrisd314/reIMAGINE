"""Stage stamps and run IDs must depend on array content, not on how an archive was written."""
import numpy as np

from reimagine.core.common import content_hash, sha256_file


def test_npz_content_hash_ignores_archive_format(tmp_path):
    a, b = tmp_path / "a.npz", tmp_path / "b.npz"
    arrays = dict(i=np.arange(10, dtype=np.int32), w=np.linspace(0, 1, 10, dtype=np.float32))
    np.savez(a, **arrays)
    np.savez_compressed(b, **arrays)
    assert sha256_file(a) != sha256_file(b)  # same arrays, different bytes
    assert content_hash(a) == content_hash(b)

    np.savez(b, i=arrays["i"], w=arrays["w"] + np.float32(1e-6))
    assert content_hash(a) != content_hash(b)
    np.savez(b, i=arrays["i"].astype(np.int64), w=arrays["w"])
    assert content_hash(a) != content_hash(b)  # dtype is part of the content


def test_other_files_use_the_file_hash(tmp_path):
    p = tmp_path / "x.json"
    p.write_text('{"k": 1}\n', encoding="utf-8")
    assert content_hash(p) == sha256_file(p)
