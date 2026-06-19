"""Subcommand: usdx-dl list - List all songs."""

from pathlib import Path
from time import perf_counter
from typing import Literal


from usdx_dl import ansi, fmt
from usdx_dl.models import SongMetadata


def main(
    output_dir: Path,
    sort_by: Literal["artist", "title", "id"],
    reverse: bool,
) -> None:
    """Args: See :func:`.args.parse`."""
    # find all songs assuming a flat directory structure
    t_start = perf_counter()
    meta_list: list[tuple[Path, SongMetadata]] = []
    for song_dir in sorted(output_dir.glob("*")):
        meta_path = song_dir / "metadata.json"
        if not song_dir.is_dir() or not meta_path.exists():
            continue
        meta = SongMetadata.load(meta_path)
        meta_list.append((song_dir, meta))
    if len(meta_list) == 0:
        print("No songs found.")
        return

    # print sorted list
    def sort_fn(item: tuple[Path, SongMetadata]) -> tuple[str, ...]:
        song_dir, meta = item
        if sort_by == "artist":
            return (meta.artist.lower(), meta.title.lower(), song_dir.name)
        if sort_by == "title":
            return (meta.title.lower(), meta.artist.lower(), song_dir.name)
        if sort_by == "id":
            return (song_dir.name.lower(), meta.artist.lower(), meta.title.lower())
        raise ValueError(f"Invalid sort key: {sort_by}")

    meta_list = sorted(meta_list, key=sort_fn, reverse=reverse)
    order = {
        "artist": [0, 1, 2],
        "title": [1, 0, 2],
        "id": [2, 0, 1],
    }[sort_by]
    t_end = perf_counter()
    elapsed = t_end - t_start

    # print result
    cols = ["Artist", "Title", "Directory"]
    col_widths = [
        max(len(meta.artist) for _, meta in meta_list),
        max(len(meta.title) for _, meta in meta_list),
        max(len(str(song_dir)) for song_dir, _ in meta_list),
    ]
    col_gap = " " * 3
    print(
        f"{ansi.BOLD}Found {len(meta_list)} {fmt.pluralize(len(meta_list), 'song')} "
        f"in {output_dir}/ "
        f"{ansi.DIM}({fmt.time(elapsed, decimals=4)}){ansi.RESET}"
    )
    print()
    print(
        ansi.BOLD
        + col_gap.join(f"{cols[i]:{col_widths[i]}}" for i in order)
        + ansi.RESET
    )
    print("-" * (sum(col_widths) + len(col_gap) * (len(cols) - 1)))
    for song_dir, meta in meta_list:
        cols = [
            f"{ansi.BOLD}{ansi.CYAN}{meta.artist:{col_widths[0]}}{ansi.RESET}",
            f"{ansi.MAGENTA}{meta.title:{col_widths[1]}}{ansi.RESET}",
            f"{ansi.DIM}{str(song_dir):{col_widths[2]}}{ansi.RESET}",
        ]
        print(col_gap.join(cols[i] for i in order))
