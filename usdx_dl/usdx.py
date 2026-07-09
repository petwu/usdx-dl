"""Various helpers to convert a song and transcribed lyrics into UltraStar format."""
# modified from https://github.com/rakuri255/UltraSinger

import math
from collections import Counter
from enum import StrEnum
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

from usdx_dl.models import MidiSegment, PitchedData, TranscribedData

__all__ = [
    "detect_bpm",
    "detect_key",
    "get_allowed_notes_for_key",
    "create_midi_segments",
    "midi_to_ultrastar_txt",
]


def detect_bpm(path: Path | str) -> float:
    """Detect the BPM (beats per minute) of a song."""
    data, sampling_rate = sf.read(path, dtype="float32")
    # transpose if stereo to match librosa's expected format
    if len(data.shape) > 1:
        data = data.T
    # convert to mono if stereo
    if data.ndim > 1:
        data = librosa.to_mono(data)

    onset_env = librosa.onset.onset_strength(y=data, sr=sampling_rate)
    tempo = librosa.feature.tempo(onset_envelope=onset_env, sr=sampling_rate)

    return tempo[0]


# scales (in semitones relative to root note)
MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11]
MINOR_SCALE = [0, 2, 3, 5, 7, 8, 10]
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def detect_key(audio_path: Path | str) -> tuple[str, str]:
    """
    Detect the key and mode (major/minor) of a song from audio file.

    Args:
        audio_path: Path to audio file

    Returns:
        Tuple of (key_note, mode) e.g., ('C', 'major') or ('A', 'minor')
    """

    y, sr = librosa.load(audio_path, sr=None, duration=60.0)  # Analyze first 60 seconds
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_avg = np.mean(chroma, axis=1)
    chroma_avg = chroma_avg / np.sum(chroma_avg)

    major_template = np.array(
        [1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1]
    )  # Major scale pattern
    minor_template = np.array(
        [1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0]
    )  # Minor scale pattern
    major_template = major_template / np.sum(major_template)
    minor_template = minor_template / np.sum(minor_template)

    best_correlation = -1
    best_key = ""
    best_mode = ""

    # Try all 12 keys
    for shift in range(12):
        shifted_major = np.roll(major_template, shift)
        shifted_minor = np.roll(minor_template, shift)

        major_corr = np.corrcoef(chroma_avg, shifted_major)[0, 1]
        minor_corr = np.corrcoef(chroma_avg, shifted_minor)[0, 1]

        if major_corr > best_correlation:
            best_correlation = major_corr
            best_key = NOTE_NAMES[shift]
            best_mode = "major"

        if minor_corr > best_correlation:
            best_correlation = minor_corr
            best_key = NOTE_NAMES[shift]
            best_mode = "minor"

    return best_key, best_mode


def get_allowed_notes_for_key(key_note: str, mode: str) -> set[str]:
    """
    Get all allowed note names for a given key across all octaves.

    Args:
        key_note: Root note (e.g., 'C', 'D#', 'F')
        mode: 'major' or 'minor'

    Returns:
        Set of allowed note names (e.g., {'C', 'D', 'E', ...})
    """
    root_idx = NOTE_NAMES.index(key_note)
    scale = MAJOR_SCALE if mode == "major" else MINOR_SCALE

    allowed_notes = set()
    for interval in scale:
        note_idx = (root_idx + interval) % 12
        allowed_notes.add(NOTE_NAMES[note_idx])

    return allowed_notes


def create_midi_segments(
    transcribed_data: list[TranscribedData],
    pitched_data: PitchedData,
    allowed_notes: set[str] | None = None,
) -> list[MidiSegment]:
    """Create MIDI segments from transcribed data

    Args:
        transcribed_data: List of transcribed data segments
        pitched_data: Pitched data containing frequencies and confidence
        allowed_notes: Optional set of allowed note names for key quantization

    Returns:
        List of MidiSegments
    """
    start_times = [segment.start for segment in transcribed_data]
    end_times = [segment.end for segment in transcribed_data]
    words = [segment.word for segment in transcribed_data]

    midi_segments = []
    for index, start_time in enumerate(start_times):
        end_time = end_times[index]
        word = str(words[index])

        midi_segment = create_midi_note_from_pitched_data(
            start_time, end_time, pitched_data, word, allowed_notes
        )
        midi_segments.append(midi_segment)

    return midi_segments


def create_midi_note_from_pitched_data(
    start_time: float,
    end_time: float,
    pitched_data: PitchedData,
    word: str,
    allowed_notes: set[str] | None = None,
) -> MidiSegment:
    """Create midi note from pitched data

    Args:
        start_time: Start time of the note
        end_time: End time of the note
        pitched_data: Pitched data containing frequencies and confidence
        word: The word/syllable for this note
        allowed_notes: Optional set of allowed note names (without octave) for key quantization

    Returns:
        One MidiSegment
    """

    start = find_nearest_index(pitched_data.times, start_time)
    end = find_nearest_index(pitched_data.times, end_time)

    if start == end:
        frequencies = [pitched_data.frequencies[start]]
        scores = [pitched_data.confidence[start]]
    else:
        frequencies = pitched_data.frequencies[start:end]
        scores = pitched_data.confidence[start:end]

    conf_f = get_frequencies_with_high_confidence(frequencies, scores)

    notes = [librosa.hz_to_note(float(freq)) for freq in conf_f]

    note = Counter(notes).most_common(1)[0][0]

    if allowed_notes is not None:
        note = quantize_note_to_key(note, allowed_notes)

    return MidiSegment(note=note, start=start_time, end=end_time, word=word)


def quantize_note_to_key(note: str, allowed_notes: set[str]) -> str:
    """
    Quantize a note to the nearest allowed note in the key.

    Args:
        note: MIDI note name (e.g., 'C4', 'D#5')
        allowed_notes: Set of allowed note names without octave

    Returns:
        Quantized note name
    """
    # Parse note and octave
    if len(note) == 0:
        return note

    # Extract note name and octave
    if len(note) >= 2 and note[-2] == "#":
        note_name = note[:-1]
        octave = note[-1]
    else:
        note_name = note[:-1] if note[-1].isdigit() else note
        octave = note[-1] if note[-1].isdigit() else ""

    # If already in key, return as is
    if note_name in allowed_notes:
        return note

    # Find nearest allowed note
    try:
        note_midi = librosa.note_to_midi(note)
    except Exception:  # pylint: disable=broad-exception-caught
        return note

    # Try all allowed notes in nearby octaves
    min_distance = float("inf")
    best_note = note

    for allowed_note_name in allowed_notes:
        # Try same octave and adjacent octaves
        for oct_offset in [-1, 0, 1]:
            if not octave:
                test_octave = 4 + oct_offset
            else:
                test_octave = int(octave) + oct_offset

            if test_octave < 0 or test_octave > 8:
                continue

            test_note = f"{allowed_note_name}{test_octave}"

            try:
                test_midi = librosa.note_to_midi(test_note)
                distance = abs(test_midi - note_midi)

                if distance < min_distance:
                    min_distance = distance
                    best_note = test_note
            except Exception:  # pylint: disable=broad-exception-caught
                continue

    return best_note


def get_frequencies_with_high_confidence(
    frequencies: list[float],
    confidences: list[float],
    threshold=0.4,
) -> list[float]:
    """Get frequency with high confidence"""
    conf_f = []
    for i, conf in enumerate(confidences):
        if conf > threshold:
            conf_f.append(frequencies[i])
    if not conf_f:
        conf_f = frequencies
    return conf_f


def find_nearest_index(array: list[float], value: float) -> int:
    """Nearest index in array"""
    idx = int(np.searchsorted(array, value, side="left"))
    if idx > 0 and (
        idx == len(array)
        or math.fabs(value - array[idx - 1]) < math.fabs(value - array[idx])
    ):
        return idx - 1

    return idx


def midi_note_to_ultrastar_note(midi_note: int) -> int:
    """Converts Midi note to UltraStar note"""

    # C4 == 48 in Midi
    ultrastar_note = midi_note - 48
    return ultrastar_note


def convert_midi_note_to_ultrastar_note(midi_segment: MidiSegment) -> int:
    """Convert midi notes to ultrastar notes"""

    note_number_librosa = librosa.note_to_midi(midi_segment.note)
    ultrastar_note = midi_note_to_ultrastar_note(int(round(note_number_librosa)))
    return ultrastar_note


def second_to_beat(seconds: float, real_bpm: float) -> float:
    """Converts seconds to beat"""
    # BPM = 60 * beat / T
    # T * BPM = 60 * beat
    # beat = T * BPM / 60
    beat = seconds * real_bpm / 60
    return beat


def real_bpm_to_ultrastar_bpm(real_bpm: float) -> float:
    """Converts real BPM to UltraStar BPM"""
    # The UltraStar BPM info is a fourth beat of the real BPM
    ultrastar_bpm = real_bpm / 4
    return ultrastar_bpm


class Tag(StrEnum):
    """Tags for Ultrastar TXT files."""

    # cSpell: disable

    # 0.2.0
    VERSION = "VERSION"  # Version of the file format: See https://usdx.eu/format/
    ARTIST = "ARTIST"
    TITLE = "TITLE"
    MP3 = "MP3"  # Removed in v2.0.0
    GAP = "GAP"
    BPM = "BPM"
    LANGUAGE = "LANGUAGE"  # Multi-language support since v1.1.0
    GENRE = "GENRE"  # Multi-language support since v1.1.0
    YEAR = "YEAR"  # Multi-language support since v1.1.0
    COVER = "COVER"  # Path to cover. Should end with `*[CO].jpg`
    BACKGROUND = "BACKGROUND"  # Path to background. Is shown when there is no video. Should end with `*[BG].jpg`
    CREATOR = "CREATOR"  # Multi-language support since v1.1.0
    COMMENT = "COMMENT"
    VIDEO = "VIDEO"
    VIDEOGAP = "VIDEOGAP"
    FILE_END = "E"
    LINEBREAK = "-"

    # 1.1.0
    AUDIO = "AUDIO"  # Its instead of MP3. Just renamed
    VOCALS = "VOCALS"  # Vocals only audio
    INSTRUMENTAL = "INSTRUMENTAL"  # Instrumental only audio
    TAGS = "TAGS"  # Tags for the song. Can be used for filtering. Separation with ","

    # 1.2.0
    VIDEOURL = "VIDEOURL"  # URL to the video file

    # Unused 0.2.0
    EDITION = "EDITION"  # Multi-language support since v1.1.0
    START = "START"
    END = "END"
    PREVIEWSTART = "PREVIEWSTART"
    MEDLEYSTARTBEAT = "MEDLEYSTARTBEAT"  # Removed in 2.0.0
    MEDLEYENDBEAT = "MEDLEYENDBEAT"  # Removed in v2.0.0
    CALCMEDLEY = "CALCMEDLEY"
    P1 = "P1"  # Only for UltraStar Deluxe
    P2 = "P2"  # Only for UltraStar Deluxe
    DUETSINGERP1 = "DUETSINGERP1"  # Removed in 1.0.0 (Used by UltraStar WorldParty)
    DUETSINGERP2 = "DUETSINGERP2"  # Removed in 1.0.0 (Used by UltraStar WorldParty)
    RESOLUTION = "RESOLUTION"  # Changes the grid resolution of the editor. Only for the editor and nothing for singing. # Removed in 1.0.0
    NOTESGAP = "NOTESGAP"  # Removed in 1.0.0
    RELATIVE = "RELATIVE"  # Removed in 1.0.0
    ENCODING = "ENCODING"  # Removed in 1.0.0

    # (Unused) 1.1.0
    PROVIDEDBY = "PROVIDEDBY"  # Should the URL from hoster server

    # (Unused) New in (unreleased) 1.2.0
    AUDIOURL = "AUDIOURL"  # URL to the audio file
    COVERURL = "COVERURL"  # URL to the cover file
    BACKGROUNDURL = "BACKGROUNDURL"  # URL to the background file

    # (Unused) New in (unreleased) 2.0.0
    MEDLEYSTART = "MEDLEYSTART"  # Rename of MEDLEYSTARTBEAT
    MEDLEYEND = "MEDLEYEND"  # Renmame of MEDLEYENDBEAT
    # These will forced to be in ms only. This will be an braking change from 1.1.0:
    # GAP: 4500
    # VIDEOGAP: 1200
    # START: 21100
    # END: 223250
    # MEDLEYSTART: 67050
    # MEDLEYEND: 960020
    # PREVIEWSTART: 45200

    # cSpell: enable


class NoteType(StrEnum):
    """Note types for Ultrastar TXT files."""

    NORMAL = ":"
    RAP = "R"
    RAP_GOLDEN = "G"
    FREESTYLE = "F"
    GOLDEN = "*"


def get_multiplier(real_bpm: float) -> int:
    """Calculates the multiplier for the BPM"""

    if real_bpm <= 0:
        raise ValueError(f"BPM must be positive and non-zero, got {real_bpm}.")

    multiplier = 1
    result = 0.0
    while result < 400:
        result = real_bpm * multiplier
        multiplier += 1
    return multiplier - 2


def midi_to_ultrastar_txt(
    midi_segments: list[MidiSegment],
    real_bpm: float,
    phrase_splits: list[float] | None,
    silence_correction: float = 1.0,
) -> tuple[list[str], float, float]:
    """Creates an Ultrastar txt file from the automation data"""
    if phrase_splits:
        phrase_splits = sorted(phrase_splits)
        while phrase_splits[0] < midi_segments[0].start:
            phrase_splits.pop(0)

    ultrastar_bpm = real_bpm_to_ultrastar_bpm(real_bpm)
    multiplication = get_multiplier(ultrastar_bpm)
    ultrastar_bpm = ultrastar_bpm * get_multiplier(ultrastar_bpm)
    silence_split_duration = (
        calculate_silent_beat_length(midi_segments) * silence_correction
    )

    gap = midi_segments[0].start

    # Write the singing part
    previous_end_beat = 0
    separated_word_silence = []  # This is a workaround for separated words that get his ends to far away

    lines = []
    for i, midi_segment in enumerate(midi_segments):
        start_time = (midi_segment.start - gap) * multiplication
        end_time = (midi_segment.end - midi_segment.start) * multiplication
        start_beat = round(second_to_beat(start_time, real_bpm))
        duration = round(second_to_beat(end_time, real_bpm))

        # Fix the round issue, so the beats don’t overlap
        start_beat = max(start_beat, previous_end_beat)
        previous_end_beat = start_beat + duration

        # Calculate the silence between the words
        if i < len(midi_segments) - 1:
            silence = midi_segments[i + 1].start - midi_segment.end
        else:
            silence = 0

        # : 10 10 10 w
        # ':'   start midi part
        # 'n1'  start at real beat
        # 'n2'  duration at real beat
        # 'n3'  pitch where 0 == C4
        # 'w'   lyric
        line = (
            f"{NoteType.NORMAL} "
            f"{str(start_beat)} "
            f"{str(duration)} "
            f"{str(convert_midi_note_to_ultrastar_note(midi_segment))} "
            f"{midi_segment.word}"
        )

        lines.append(line)

        # detect silence between words
        if not midi_segment.word.endswith(" "):
            separated_word_silence.append(silence)
            continue

        end_of_phrase = False
        if i < len(midi_segments) - 1:
            if phrase_splits is not None:
                end_of_phrase = (
                    len(phrase_splits) > 0
                    and midi_segments[i + 1].start >= phrase_splits[0]
                )
                if end_of_phrase:
                    phrase_splits.pop(0)
            else:
                end_of_phrase = (
                    silence_split_duration != 0
                    and silence > silence_split_duration
                    or any(s > silence_split_duration for s in separated_word_silence)
                )

        if end_of_phrase:
            # - 10
            # '-' end of current sing part
            # 'n1' show next at time in real beat
            show_next = (
                second_to_beat(midi_segment.end - gap, real_bpm) * multiplication
            )
            linebreak = f"{Tag.LINEBREAK} {str(round(show_next))}"
            lines.append(linebreak)
        separated_word_silence = []
    lines.append(Tag.FILE_END)

    return lines, ultrastar_bpm, gap


def calculate_silent_beat_length(midi_segments: list[MidiSegment]):
    """Calculate the deviation of the silent parts."""
    if len(midi_segments) < 5:
        return 0

    silent_parts = [
        s2.start - s1.end for s1, s2 in zip(midi_segments[:-1], midi_segments[1:])
    ]
    sorted_parts = sorted(silent_parts)
    filtered_parts = [x for x in sorted_parts if x > 0]
    mean = sum(filtered_parts) / len(filtered_parts)
    # median = filtered_parts[len(filtered_parts) // 2]
    return mean
