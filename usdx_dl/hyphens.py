"""Hyphenation module."""
# modified from https://github.com/rakuri255/UltraSinger

import copy
import string

from hyphen import Hyphenator

from usdx_dl.models import TranscribedData

__all__ = ["hyphenate_transcription"]


def hyphenate_transcription(
    transcribed_data: list[TranscribedData],
    language: str,
) -> list[TranscribedData]:
    """Hyphenate each word in the transcribed data.

    Args:
        transcribed_data: Transcription.
        language: Locale name, e.g. "en_US", "de_DE".

    Returns:
        Hyphenated transcription.
    """

    hyphenator = Hyphenator(language)
    hyphenated_words = [
        hyphenate_word(data.word, hyphenator) for data in transcribed_data
    ]

    return add_hyphen_to_data(transcribed_data, hyphenated_words)


def hyphenate_word(word: str, hyphenator: Hyphenator) -> list[str] | None:
    """Hyphenate a single word."""

    cleaned_string, removed_indices, removed_symbols = clean_word(word)

    # Hyphenation of word longer than 100 characters throws exception
    if len(cleaned_string) > 100:
        return None

    syllabus = hyphenator.syllables(cleaned_string)

    length = len(syllabus)
    if length > 1:
        hyphen = []
        for i in range(length):
            hyphen.append(syllabus[i])
        hyphen = insert_removed_symbols(hyphen, removed_indices, removed_symbols)
    else:
        hyphen = None

    return hyphen


def clean_word(word: str):
    """Remove punctuation from word"""
    cleaned_string = ""
    removed_indices = []
    removed_symbols = []
    for i, char in enumerate(word):
        if char not in string.punctuation and char not in " ":
            cleaned_string += char
        else:
            removed_indices.append(i)
            removed_symbols.append(char)
    return cleaned_string, removed_indices, removed_symbols


def insert_removed_symbols(separated_array, removed_indices, symbols):
    """Insert symbols into the syllables"""
    result = []
    symbol_index = 0
    i = 0

    # Add removed symbols to the syllables
    for syllable in separated_array:
        tmp = ""
        for char in syllable:
            while i in removed_indices:
                tmp += symbols[symbol_index]
                symbol_index += 1
                i += 1
            tmp += char
            i += 1
        result.append(tmp)

    # Add remaining symbols to the last syllable
    if symbol_index < len(symbols):
        tmp = result[-1]
        for i in range(symbol_index, len(symbols)):
            tmp += symbols[i]
        result[-1] = tmp

    return result


def add_hyphen_to_data(
    transcribed_data: list[TranscribedData],
    hyphenated_words: list[list[str] | None],
) -> list[TranscribedData]:
    """Add hyphen to transcribed data return new data list"""
    new_data = []

    for i, data in enumerate(transcribed_data):
        hyphenated_word = hyphenated_words[i]
        if not hyphenated_word:
            new_data.append(data)
        else:
            chunk_duration = data.end - data.start
            chunk_duration = chunk_duration / (len(hyphenated_word))

            next_start = data.start
            for j in enumerate(hyphenated_word):
                hyphenated_word_index = j[0]
                dup = copy.copy(data)
                dup.start = next_start
                next_start = data.end - chunk_duration * (
                    len(hyphenated_word) - 1 - hyphenated_word_index
                )
                dup.end = next_start
                dup.word = hyphenated_word[hyphenated_word_index]
                dup.is_hyphen = True
                if hyphenated_word_index == len(hyphenated_word) - 1:
                    dup.is_word_end = True
                else:
                    dup.is_word_end = False
                new_data.append(dup)

    return new_data


def remove_punctuation_(
    transcribed_data: list[TranscribedData],
    punctuation: str = string.punctuation,
) -> list[TranscribedData]:
    """Remove unnecessary punctuations from transcribed data."""
    for data in transcribed_data:
        data.word = data.word.translate({ord(i): None for i in punctuation})
    return transcribed_data
