"""Subcommand: usdx-dl list - List all songs."""

import re
from pathlib import Path
from time import perf_counter
from typing import Literal

from usdx_dl import ansi, fmt, models
from usdx_dl.models import SongMetadata


def main(
    output_dir: Path,
    sort_by: Literal["artist", "title", "id"],
    reverse: bool,
) -> None:
    """Args: See :func:`.args.parse`."""
    # find all songs assuming a flat directory structure
    t_start = perf_counter()
    meta_list = find_songs(output_dir, sort_by, reverse)
    if len(meta_list) == 0:
        print("No songs found.")
        return
    t_end = perf_counter()
    elapsed = t_end - t_start

    # print result
    order = __order(sort_by)
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


def find_songs(
    output_dir: Path,
    sort_by: Literal["artist", "title", "id"],
    reverse: bool,
) -> list[tuple[Path, SongMetadata]]:
    """Find all songs in the output directory and return a list of
    (song_dir, metadata) tuples."""

    meta_list: list[tuple[Path, SongMetadata]] = []
    for song_dir in sorted(output_dir.glob("*")):
        meta_path = song_dir / "metadata.json"
        txt_path = song_dir / "song.txt"
        if not song_dir.is_dir() or not meta_path.exists() or not txt_path.exists():
            continue
        meta = models.from_json(SongMetadata, meta_path)
        meta_list.append((song_dir, meta))
    if len(meta_list) == 0:
        return []

    # print sorted list
    order = __order(sort_by)
    sort_fn = __sort_key(order, natural=True)
    meta_list = sorted(meta_list, key=sort_fn, reverse=reverse)

    return meta_list


def __order(sort_by: Literal["artist", "title", "id"]) -> list[int]:
    return {
        "artist": [0, 1, 2],
        "title": [1, 0, 2],
        "id": [2, 0, 1],
    }[sort_by]


def __sort_key(order: list[int], natural: bool = False):
    assert len(order) == 3 and set(order) == {0, 1, 2}

    def fn(item: tuple[Path, SongMetadata]) -> str | list[int | str]:
        song_dir, meta = item
        sort_info = [meta.artist, meta.title, song_dir.name]
        sort_info = [sort_info[i] for i in order]
        sort_str = " ".join(str(x) for x in sort_info).lower()
        if natural:
            return [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", sort_str)]
        return sort_str

    return fn
