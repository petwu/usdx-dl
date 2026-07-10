import tempfile
from pathlib import Path

from usdx_dl import func_utils


def test_mtime_cache():
    """Test the mtime_cache decorator."""
    call_count = 0

    @func_utils.mtime_cache
    def read_file(path: Path | str) -> str | None:
        nonlocal call_count
        call_count += 1
        path = Path(path)
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    with tempfile.TemporaryDirectory() as tmp_dir:
        # first call should return None and increment call_count only once
        tmp_path = Path(tmp_dir) / "test.txt"
        for _ in range(3):
            assert read_file(tmp_path) is None
        assert call_count == 1

        # invalidate cache by creating the file
        tmp_path.write_text("Hello, world!", encoding="utf-8")
        for _ in range(3):
            assert read_file(tmp_path) == "Hello, world!"
        assert call_count == 2

        # invalidate the cache by modifying the file
        tmp_path.write_text("Goodbye, world!", encoding="utf-8")
        for _ in range(3):
            assert read_file(tmp_path) == "Goodbye, world!"
        assert call_count == 3

        # a few more cached calls
        for _ in range(3):
            assert read_file(tmp_path) == "Goodbye, world!"
        assert call_count == 3

        # a few more cached calls with an different path that points to the same file
        tmp_path_variant = tmp_path.relative_to(Path.cwd(), walk_up=True)
        assert tmp_path != tmp_path_variant
        for _ in range(3):
            assert read_file(tmp_path_variant) == "Goodbye, world!"
        assert call_count == 3
