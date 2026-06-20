# usdx-dl

Download all necessary files (txt, cover, audio, video, etc.) for UltraStar Deluxe and similar games that support UltraStar .txt files.

## 🚀 Getting Started

Install the following **dependencies**:

- [uv](https://docs.astral.sh/uv)
- [ffmpeg](https://www.ffmpeg.org/)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)

The run:

```sh
uv venv
uv pip install --torch-backend auto --editable .
usdx-dl --help
```

## 🎓 Example Usage

> [!tip]
> Providing USDB links is preferred, as it typically provides quality TXT files.
> When providing only a YouTube link, the TXT is generated using AI models, which can be less accurate.
>
> Find popular songs [here](https://usdb.animux.de/?link=list&start=0&order=views&ud=desc).

### USDB

```sh
usdx-dl "https://usdb.animux.de/?link=detail&id=1368"
```

This performs the following steps:

1. Download TXT from USDB.
2. Download audio and video from YouTube.
3. Split vocals with [demucs](https://github.com/facebookresearch/demucs).

### YouTube

```sh
usdx-dl "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

This performs the following steps:

1. Download audio and video from YouTube.
2. Split vocals with [demucs](https://github.com/facebookresearch/demucs).
3. Download lyrics from [lrclib.net](https://lrclib.net).
4. Predict BPM, key, etc.
5. Transcribe using [whisperX](https://github.com/m-bain/whisperX).
6. Predict pitch using [SwiftF0](https://github.com/lars76/swift-f0).
7. Generate TXT files.

### Batch Processing

You can also provide a text file containing one link/ID per line:

```sh
usdx-dl songs.txt [--non-interactive]
```

## 🎙️ Start Singing

1. Download and install UltraStar Deluxe from [here](https://usdx.eu/downloads).
2. Copy or symlink your `songs/` directory into the games' config directory, or add them to the `config.ini` (`SongDir1=`, etc.). The config directory is platform-specific:
   - AppImage: `~/.ultrastardx`
   - Flatpak: `~/.var/app/eu.usdx.UltraStarDeluxe/.ultrastardx`
3. Start them game, configure your microphone and start singing!

## 🙏 Credits

Thanks to [UltraSinger](https://github.com/rakuri255/UltraSinger) for the code path that generates UltraStar .txt files using [whisperX](https://github.com/m-bain/whisperX) and [SwiftF0](https://github.com/lars76/swift-f0).
