"""Syllable handling."""

import copy

import librosa

from usdx_dl.models import TranscribedData
from usdx_dl.usdx import MidiSegment

__all__ = [
    "split_into_segments",
    "merge_segments",
]


def split_into_segments(
    transcribed_data: list[TranscribedData],
    bpm: float,
) -> list[TranscribedData]:
    """Split every syllable into sub-segments

    This splits long syllables (including hyphenated ones) into smaller segments
    to allow detect for pitch changes within a syllable (e.g., singing a scale).
    """
    syllable_segment_size = get_16th_note_second(bpm)
    note_32nd = get_32nd_note_second(bpm)

    segment_size_decimal_points = len(str(syllable_segment_size).split(".")[1])
    new_data = []

    for i, data in enumerate(transcribed_data):
        duration = data.end - data.start

        # If duration is less than or equal to a 16th note, don't split
        if duration <= syllable_segment_size:
            new_data.append(data)
            continue

        has_space = str(data.word).endswith(" ")
        first_segment = copy.deepcopy(data)
        filler_words_start = data.start + syllable_segment_size
        remainder = data.end - filler_words_start
        first_segment.end = filler_words_start
        if has_space:
            first_segment.word = first_segment.word[:-1]

        first_segment.is_word_end = False
        new_data.append(first_segment)

        full_segments, partial_segment = divmod(remainder, syllable_segment_size)

        if full_segments >= 1:
            first_segment.is_hyphen = True
            for i in range(int(full_segments)):
                start = filler_words_start + round(
                    i * syllable_segment_size, segment_size_decimal_points
                )
                end = start + syllable_segment_size
                segment = TranscribedData(
                    word="~",
                    start=start,
                    end=end,
                    is_hyphen=True,
                    is_word_end=False,
                )
                new_data.append(segment)

        # Only add a partial_segment if it's at least as long as a 32nd note
        # Otherwise add it to the last note
        if partial_segment >= note_32nd:
            first_segment.is_hyphen = True
            start = filler_words_start + round(
                full_segments * syllable_segment_size, segment_size_decimal_points
            )
            end = start + partial_segment
            segment = TranscribedData(
                word="~",
                start=start,
                end=end,
                is_hyphen=True,
                is_word_end=False,
            )
            new_data.append(segment)
        elif full_segments >= 1 or len(new_data) > 0:
            # Add remaining time to the last note
            new_data[-1].end += partial_segment

        if has_space:
            new_data[-1].word += " "
            new_data[-1].is_word_end = True
    return new_data


def merge_segments(
    midi_segments: list[MidiSegment],
    transcribed_data: list[TranscribedData],
    bpm: float,
) -> tuple[list[MidiSegment], list[TranscribedData]]:
    """Merge sub-segments of a syllable where the pitch is the same

    This function handles three cases:
    1. Merge consecutive ~ segments with the SAME pitch (same note held)
    2. Detect and merge SLIDES: short ~ segments with ±1-2 semitone jumps between
       syllables.
    3. Merge ANY consecutive segments (including regular syllables) with the SAME
       pitch into one word.
    """

    note_16th = get_16th_note_second(bpm)
    # Slides are typically very short (1-2 16th notes)
    max_slide_duration = note_16th * 2

    new_data: list[TranscribedData] = []
    new_midi: list[MidiSegment] = []

    previous_data = None

    for i, data in enumerate(transcribed_data):
        # Check if previous element exists
        is_same_note = i > 0 and midi_segments[i].note == midi_segments[i - 1].note
        has_breath_pause = False

        if previous_data is not None:
            has_breath_pause = (data.start - previous_data.end) > note_16th

        # Check if current word is a ~ segment (continuation marker)
        current_word_stripped = str(data.word).strip()
        is_tilde_segment = current_word_stripped == "~"

        # Slide detection: Detect short ~ segments with small pitch jumps
        is_potential_slide = False
        if i > 0 and is_tilde_segment:
            duration = data.end - data.start

            # Calculate pitch jump in semitones
            try:
                prev_midi = librosa.note_to_midi(midi_segments[i - 1].note)
                curr_midi = librosa.note_to_midi(midi_segments[i].note)
                semitone_diff = abs(curr_midi - prev_midi)

                # Slide: Short duration AND small pitch jump (1-2 semitones)
                is_potential_slide = (
                    duration <= max_slide_duration
                    and semitone_diff <= 2
                    and semitone_diff > 0
                )
            except Exception:  # pylint: disable=broad-exception-caught
                # Ignore slide detection on error
                pass

        # Check if current segment should be merged with previous due to same pitch
        should_merge_same_pitch = False
        if (
            i > 0
            and previous_data is not None
            and not is_tilde_segment  # Not a ~ segment
            and is_same_note
            and not has_breath_pause
            and not previous_data.is_word_end
        ):  # Don't merge across word boundaries
            should_merge_same_pitch = True

        should_merge_tilde = (
            is_tilde_segment
            and previous_data is not None
            and (is_same_note or is_potential_slide)
            and not has_breath_pause
        )

        if should_merge_tilde:
            new_data[-1].end = data.end
            new_midi[-1].end = data.end

            # For slides: Keep the original note (not the transition note)
            if is_potential_slide and not is_same_note:
                new_midi[-1].note = midi_segments[i - 1].note

            # Take over space and word_end flag from current segment
            # "~ " means end of word - add space to previous segment
            if str(data.word).endswith(" "):
                if not new_data[-1].word.endswith(" "):
                    new_data[-1].word += " "
                if not new_midi[-1].word.endswith(" "):
                    new_midi[-1].word += " "
                new_data[-1].is_word_end = True

        elif should_merge_same_pitch:
            # Merge regular syllable with previous syllable (same pitch)
            new_data[-1].end = data.end
            new_midi[-1].end = data.end

            # Check if current word has space at end before stripping
            has_space = str(data.word).endswith(" ")

            # Concatenate the words (remove trailing space from previous, add current word)
            prev_word = new_data[-1].word.rstrip()
            curr_word = data.word.rstrip()

            # Remove ~ from BOTH previous and current word if present
            if prev_word == "~":
                prev_word = ""
            if curr_word.startswith("~"):
                curr_word = curr_word[1:]

            # Concatenate
            new_data[-1].word = prev_word + curr_word
            new_midi[-1].word = prev_word + curr_word

            # Preserve space at end if current segment had it
            if has_space:
                new_data[-1].word += " "
                new_midi[-1].word += " "

            if data.is_word_end:
                new_data[-1].is_word_end = True
                new_data[-1].is_hyphen = False
            else:
                # Keep hyphen status if either segment was hyphenated
                new_data[-1].is_hyphen = new_data[-1].is_hyphen or data.is_hyphen

        else:
            # Add as new segment
            new_data.append(data)
            new_midi.append(midi_segments[i])

        previous_data = data

    return new_midi, new_data


def get_32nd_note_second(bpm: float):
    """Converts a beat to a 1/32 note in second"""
    return 60 / bpm / 8


def get_16th_note_second(bpm: float):
    """Converts a beat to a 1/16 note in second"""
    return 60 / bpm / 4
