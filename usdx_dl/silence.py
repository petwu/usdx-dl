"""Silence processing."""
# modified from https://github.com/rakuri255/UltraSinger

from pathlib import Path

import librosa
import soundfile as sf
from pydub import AudioSegment, silence

from usdx_dl.models import TranscribedData

__all__ = [
    "get_sections",
    "remove_from_transcription",
    "mute_non_singing_parts",
]


def get_sections(
    audio_path: Path | str,
    min_silence_len: int = 50,
    silence_thresh: int = -50,
) -> list[tuple[float, float]]:
    """Detect silent sections."""
    y = AudioSegment.from_file(audio_path, format=Path(audio_path).suffix[1:])
    s = silence.detect_silence(
        y,
        min_silence_len=min_silence_len,
        silence_thresh=silence_thresh,
    )
    s = [((start / 1000), (end / 1000)) for start, end in s]  # convert to sec
    return s


def remove_from_transcription(
    audio_path: Path | str,
    transcribed_data: list[TranscribedData],
) -> list[TranscribedData]:
    """Remove silence from given transcription data"""

    silence_timestamps = get_sections(audio_path)
    new_transcribed_data = []

    for data in transcribed_data:
        new_transcribed_data.append(data)

        origin_end = data.end
        was_split = False

        for silence_start, silence_end in silence_timestamps:
            # |    ****    | silence
            # |  **    **  | data
            # |0 1 2 3 4 5 | time
            if silence_start > origin_end or silence_end < data.start:
                continue

            # |    **  **    | silence
            # |  **********  | data
            # |0 1 2 3 4 5 6 | time
            if silence_start >= data.start and silence_end <= origin_end:
                next_index = silence_timestamps.index((silence_start, silence_end)) + 1
                if (
                    next_index < len(silence_timestamps)
                    and silence_timestamps[next_index][0] < origin_end
                ):
                    split_end = silence_timestamps[next_index][0]

                    if silence_timestamps[next_index][1] >= origin_end:
                        split_word = "~ "
                        is_word_end = True
                    else:
                        split_word = "~"
                        is_word_end = False
                else:
                    split_end = origin_end
                    split_word = "~ "
                    is_word_end = True

                split_data = TranscribedData(
                    score=data.score,
                    word=split_word,
                    end=split_end,
                    start=silence_end,
                    is_word_end=is_word_end,
                )

                if not was_split:
                    data.end = silence_start

                    if data.end - data.start < 0.1:
                        data.start = silence_end
                        data.end = split_end
                        continue

                    if split_data.end - split_data.start <= 0.1:
                        continue

                    data.is_word_end = False

                    # Remove last whitespace from the data.word
                    if data.word[-1] == " ":
                        data.word = data.word[:-1]

                if split_data.end - split_data.start > 0.1:
                    was_split = True
                    new_transcribed_data.append(split_data)
                elif split_word == "~ " and not data.is_word_end:
                    if new_transcribed_data[-1].word[-1] != " ":
                        new_transcribed_data[-1].word += " "
                    new_transcribed_data[-1].is_word_end = True

                continue

            # |    ****  | silence
            # |     **   | data
            # |0 1 2 3 4 | time
            if silence_start < data.start and silence_end > origin_end:
                new_transcribed_data.remove(data)
                break

            # |    ****    | silence
            # |      ****  | data
            # |0 1 2 3 4 5 | time
            if silence_start < data.start:
                data.start = silence_end

            # |    ****  | silence
            # |  ****    | data
            # |0 1 2 3 4 | time
            if silence_end > origin_end:
                data.end = silence_start

            # |    ****  | silence
            # |  **      | data
            # |0 1 2 3 4 | time
            if silence_start > origin_end:
                # Nothing to do with this word anymore, go to next word
                break
    return new_transcribed_data


def mute_non_singing_parts(input_path: Path | str, output_path: Path | str) -> None:
    """Mute parts without singing/vocals."""
    silence_sections = get_sections(input_path)
    y, sr = librosa.load(input_path, sr=None)
    # Mute the parts of the audio with no singing
    for i in silence_sections:
        # Define the time range to mute

        start_time = i[0]  # Start time in seconds
        end_time = i[1]  # End time in seconds

        # Convert time to sample indices
        start_sample = int(start_time * sr)
        end_sample = int(end_time * sr)

        y[start_sample:end_sample] = 0
    sf.write(output_path, y, sr)  # type: ignore
