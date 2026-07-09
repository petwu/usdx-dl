"""A pure-Python (NumPy-only) re-implementation of the *inference* path of the
`fastText <https://github.com/facebookresearch/fastText>`_ library, ported from
`fasttext-predict <https://github.com/searxng/fasttext-predict>`_.

Also includes additional utilities to download and cache the pre-trained models
from `here <https://fasttext.cc/docs/en/language-identification.html>`_ such
that a model can be loaded by name.

Note that the implementation is not completely API-compatible.

Example:
>>> import fasttext_np
>>> model = fasttext_np.load_model("lid.176.ftz")
>>> labels, probs = model.predict('This is a test sentence.', k=2)
"""
# pylint: disable=missing-class-docstring,missing-function-docstring
# cSpell: ignore qout maxn minn dsub cstring subwords qnorm nsubq sungetc calcsize
# cSpell: ignore CBOW KSUB HS NS OVA SG SUP

import abc
import heapq
import math
import os
import struct
from collections.abc import Sequence
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Self

import numpy as np
import requests

__all__ = ["load_model"]

# --------------------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------------------

FASTTEXT_VERSION = 12
FASTTEXT_MAGIC = 793712314

EOS = b"</s>"
BOW = b"<"
EOW = b">"
WHITESPACE = frozenset(b" \n\r\t\v\f\0")


class ModelName(IntEnum):
    CBOW = 1
    SG = 2
    SUP = 3


class LossName(IntEnum):
    HS = 1
    NS = 2
    SOFTMAX = 3
    OVA = 4


class EntryType(IntEnum):
    WORD = 0
    LABEL = 1


# --------------------------------------------------------------------------------------
# Binary reader
# --------------------------------------------------------------------------------------


class Reader:
    """Sequential little-endian binary reader over an in-memory buffer."""

    __slots__ = ("buf", "pos")

    def __init__(self, buf: bytes):
        self.buf = buf
        self.pos = 0

    def _unpack(self, fmt: str):
        (val,) = struct.unpack_from(fmt, self.buf, self.pos)
        self.pos += struct.calcsize(fmt)
        return val

    def i32(self) -> int:
        return self._unpack("<i")

    def i64(self) -> int:
        return self._unpack("<q")

    def u8(self) -> int:
        return self._unpack("<B")

    def f64(self) -> float:
        return self._unpack("<d")

    def bool(self) -> bool:
        return self._unpack("<?")

    def cstring(self) -> bytes:
        start = self.pos
        end = self.buf.index(0, start)
        s = self.buf[start:end]
        self.pos = end + 1
        return s

    def f32_array(self, n: int) -> np.ndarray:
        arr = np.frombuffer(self.buf, dtype="<f4", count=n, offset=self.pos).copy()
        self.pos += 4 * n
        return arr

    def u8_array(self, n: int) -> np.ndarray:
        arr = np.frombuffer(self.buf, dtype=np.uint8, count=n, offset=self.pos).copy()
        self.pos += n
        return arr


# --------------------------------------------------------------------------------------
# Args
# --------------------------------------------------------------------------------------


@dataclass
class Args:
    dim: int = 100
    ws: int = 5
    epoch: int = 5
    min_count: int = 5
    neg: int = 5
    word_ngrams: int = 1
    loss: LossName = LossName.NS
    model: ModelName = ModelName.SG
    bucket: int = 2_000_000
    minn: int = 3
    maxn: int = 6
    lr_update_rate: int = 100
    t: float = 1e-4
    qout: bool = False
    label: bytes = b"__label__"

    @classmethod
    def load(cls, r: Reader) -> Self:
        return cls(
            dim=r.i32(),
            ws=r.i32(),
            epoch=r.i32(),
            min_count=r.i32(),
            neg=r.i32(),
            word_ngrams=r.i32(),
            loss=LossName(r.i32()),
            model=ModelName(r.i32()),
            bucket=r.i32(),
            minn=r.i32(),
            maxn=r.i32(),
            lr_update_rate=r.i32(),
            t=r.f64(),
        )


# --------------------------------------------------------------------------------------
# Matrix representations
# --------------------------------------------------------------------------------------


class ProductQuantizer:
    KSUB = 256

    def __init__(
        self,
        dim: int,
        nsubq: int,
        dsub: int,
        last_dsub: int,
        centroids: np.ndarray,
    ) -> None:
        self.dim = dim
        self.nsubq = nsubq
        self.dsub = dsub
        self.last_dsub = last_dsub
        self.centroids = centroids

    @classmethod
    def load(cls, r: Reader) -> Self:
        dim = r.i32()
        nsubq = r.i32()
        dsub = r.i32()
        last_dsub = r.i32()
        centroids = r.f32_array(dim * cls.KSUB)
        return cls(dim, nsubq, dsub, last_dsub, centroids)

    def centroid(self, m: int, code: int) -> np.ndarray:
        if m == self.nsubq - 1:
            start = m * self.KSUB * self.dsub + code * self.last_dsub
            length = self.last_dsub
        else:
            start = (m * self.KSUB + code) * self.dsub
            length = self.dsub
        return self.centroids[start : start + length]

    def mul_code(self, x: np.ndarray, codes_row: np.ndarray, alpha: float) -> float:
        total = 0.0
        for m, code in enumerate(codes_row):
            c = self.centroid(m, int(code))
            seg = x[m * self.dsub : m * self.dsub + len(c)]
            total += float(seg @ c)
        return total * alpha

    def add_code(self, x: np.ndarray, codes_row: np.ndarray, alpha: float) -> None:
        for m, code in enumerate(codes_row):
            c = self.centroid(m, int(code))
            x[m * self.dsub : m * self.dsub + len(c)] += alpha * c


class WeightMatrix(abc.ABC):
    """Common interface implemented by DenseMatrix and QuantMatrix."""

    m: int
    n: int

    @abc.abstractmethod
    def dot_row(self, hidden: np.ndarray, i: int) -> float: ...

    @abc.abstractmethod
    def dot_all(self, hidden: np.ndarray) -> np.ndarray: ...

    @abc.abstractmethod
    def row_mean(self, indices: Sequence[int]) -> np.ndarray: ...


class DenseMatrix(WeightMatrix):
    def __init__(self, m: int, n: int, data: np.ndarray) -> None:
        self.m = m
        self.n = n
        self.data = data

    @classmethod
    def load(cls, r: Reader) -> Self:
        m = r.i64()
        n = r.i64()
        data = r.f32_array(m * n).reshape(m, n)
        return cls(m, n, data)

    def dot_row(self, hidden: np.ndarray, i: int) -> float:
        return float(self.data[i] @ hidden)

    def dot_all(self, hidden: np.ndarray) -> np.ndarray:
        return (self.data @ hidden).astype(np.float32)

    def row_mean(self, indices: Sequence[int]) -> np.ndarray:
        idx = np.fromiter(indices, dtype=np.int64)
        return self.data[idx].mean(axis=0).astype(np.float32)


class QuantMatrix(WeightMatrix):
    def __init__(
        self,
        m: int,
        n: int,
        codes: np.ndarray,
        pq: ProductQuantizer,
        norm_codes: np.ndarray | None,
        npq: ProductQuantizer | None,
    ) -> None:
        self.m = m
        self.n = n
        self.codes = codes
        self.norm_codes = norm_codes
        self.pq: ProductQuantizer = pq
        self.npq: ProductQuantizer | None = npq

    @classmethod
    def load(cls, r: Reader) -> Self:
        qnorm = r.bool()
        m = r.i64()
        n = r.i64()
        code_size = r.i32()
        codes_flat = r.u8_array(code_size)
        pq = ProductQuantizer.load(r)
        codes = codes_flat.reshape(m, pq.nsubq)
        norm_codes = npq = None
        if qnorm:
            norm_codes = r.u8_array(m)
            npq = ProductQuantizer.load(r)
        return cls(m, n, codes, pq, norm_codes, npq)

    def row_norm(self, i: int) -> float:
        if self.npq is not None:
            assert self.norm_codes is not None
            return float(self.npq.centroid(0, int(self.norm_codes[i]))[0])
        return 1.0

    def dot_row(self, hidden: np.ndarray, i: int) -> float:
        return self.pq.mul_code(hidden, self.codes[i], self.row_norm(i))

    def dot_all(self, hidden: np.ndarray) -> np.ndarray:
        return np.fromiter(
            (self.dot_row(hidden, i) for i in range(self.m)),
            dtype=np.float32,
            count=self.m,
        )

    def add_row_to(self, x: np.ndarray, i: int, alpha: float = 1.0) -> None:
        self.pq.add_code(x, self.codes[i], alpha * self.row_norm(i))

    def row_mean(self, indices: Sequence[int]) -> np.ndarray:
        x = np.zeros(self.n, dtype=np.float32)
        for i in indices:
            self.add_row_to(x, i)
        return x / len(indices)


# --------------------------------------------------------------------------------------
# Dictionary
# --------------------------------------------------------------------------------------


def fnv_hash(data: bytes) -> int:
    """FNV-1a variant using *signed* char xor."""
    h = 2166136261
    for byte in data:
        h = (h ^ (byte - 256 if byte >= 128 else byte)) & 0xFFFFFFFF
        h = (h * 16777619) & 0xFFFFFFFF
    return h


@dataclass
class Word:
    word: bytes
    count: int
    type: EntryType
    subwords: list[int]


class Dictionary:
    def __init__(self, args: Args):
        self.args = args
        self.n_words = 0
        self.n_labels = 0
        self.n_tokens = 0
        self.prune_idx_size = -1
        self.words: list[Word] = []
        self.prune_idx: dict[int, int] = {}
        self.word2int: list[int] = []

    @property
    def is_pruned(self) -> bool:
        return self.prune_idx_size >= 0

    def find(self, word: bytes, h: int) -> int:
        size = len(self.word2int)
        idx = h % size
        while self.word2int[idx] != -1 and self.words[self.word2int[idx]].word != word:
            idx = (idx + 1) % size
        return idx

    def get_id(self, word: bytes, h: int) -> int:
        return self.word2int[self.find(word, h)]

    def push_hash(self, out: list[int], idx: int) -> None:
        if self.prune_idx_size == 0 or idx < 0:
            return
        if self.prune_idx_size > 0:
            idx = self.prune_idx.get(idx, -1)
            if idx < 0:
                return
        out.append(self.n_words + idx)

    def compute_subwords(self, word: bytes, out: list[int]) -> None:
        minn, maxn, bucket = self.args.minn, self.args.maxn, self.args.bucket
        n_ = len(word)
        for i in range(n_):
            if (word[i] & 0xC0) == 0x80:
                continue
            ngram = bytearray()
            j = i
            n = 1
            while j < n_ and n <= maxn:
                ngram.append(word[j])
                j += 1
                while j < n_ and (word[j] & 0xC0) == 0x80:
                    ngram.append(word[j])
                    j += 1
                if n >= minn and not (n == 1 and (i == 0 or j == n_)):
                    h = fnv_hash(bytes(ngram)) % bucket
                    self.push_hash(out, h)
                n += 1

    def add_subwords(self, out: list[int], token: bytes, wid: int) -> None:
        if wid < 0:
            if token != EOS:
                self.compute_subwords(BOW + token + EOW, out)
        elif self.args.maxn <= 0:
            out.append(wid)
        else:
            out.extend(self.words[wid].subwords)

    def add_word_ngrams(self, line: list[int], hashes: list[int], n: int) -> None:
        bucket = self.args.bucket
        mask = (1 << 64) - 1
        for i, hi in enumerate(hashes):
            h = hi & mask
            for j in range(i + 1, min(len(hashes), i + n)):
                h = (h * 116049371 + hashes[j]) & mask
                self.push_hash(line, h % bucket)

    def get_type(self, token: bytes) -> EntryType:
        return EntryType.LABEL if token.startswith(self.args.label) else EntryType.WORD

    def get_label(self, lid: int) -> bytes:
        if not 0 <= lid < self.n_labels:
            raise ValueError(f"Label id is out of range [0, {self.n_labels}]")
        return self.words[lid + self.n_words].word.replace(self.args.label, b"", 1)

    def get_counts(self, entry_type: EntryType) -> list[int]:
        return [w.count for w in self.words if w.type == entry_type]

    def get_line(self, tokens: Sequence[bytes]) -> tuple[list[int], list[int]]:
        words: list[int] = []
        labels: list[int] = []
        hashes: list[int] = []
        for token in tokens:
            h = fnv_hash(token)
            wid = self.get_id(token, h)
            entry_type = self.get_type(token) if wid < 0 else self.words[wid].type
            if entry_type is EntryType.WORD:
                self.add_subwords(words, token, wid)
                hashes.append(h)
            elif entry_type is EntryType.LABEL and wid >= 0:
                labels.append(wid - self.n_words)
            if token == EOS:
                break
        self.add_word_ngrams(words, hashes, self.args.word_ngrams)
        return words, labels

    @classmethod
    def load(cls, r: Reader, args: Args) -> Self:
        d = cls(args)
        size = r.i32()
        d.n_words = r.i32()
        d.n_labels = r.i32()
        d.n_tokens = r.i64()
        d.prune_idx_size = r.i64()

        d.words = [
            Word(word=r.cstring(), count=r.i64(), type=EntryType(r.u8()), subwords=[])
            for _ in range(size)
        ]
        d.prune_idx = {r.i32(): r.i32() for _ in range(max(d.prune_idx_size, 0))}

        for i, entry in enumerate(d.words):
            subwords = [i]
            if entry.word != EOS:
                d.compute_subwords(BOW + entry.word + EOW, subwords)
            entry.subwords = subwords

        word2int_size = math.ceil(size / 0.7)
        d.word2int = [-1] * word2int_size
        for i, entry in enumerate(d.words):
            idx = d.find(entry.word, fnv_hash(entry.word))
            d.word2int[idx] = i
        return d


# --------------------------------------------------------------------------------------
# Tokenizer
# --------------------------------------------------------------------------------------


def tokenize(text: str) -> list[bytes]:
    """Splits `text` into fastText tokens, ending with the EOS token."""
    if not text.endswith("\n"):
        text += "\n"
    data = text.encode("utf-8")
    tokens: list[bytes] = []
    word = bytearray()
    i = 0
    n = len(data)
    while i < n:
        c = data[i]
        i += 1
        if c in WHITESPACE:
            if not word:
                if c == 0x0A:  # \n
                    tokens.append(EOS)
                continue
            if c == 0x0A:
                i -= 1  # unget: newline still needs to be seen next iteration
            tokens.append(bytes(word))
            word.clear()
        else:
            word.append(c)
    if word:
        tokens.append(bytes(word))
    return tokens


# --------------------------------------------------------------------------------------
# Losses
# --------------------------------------------------------------------------------------


def std_log(x: float) -> float:
    return math.log(x + 1e-5)


def top_k(k: int, threshold: float, output: np.ndarray) -> list[tuple[float, int]]:
    heap: list[tuple[float, int]] = []
    for i, val in enumerate(output):
        if val < threshold:
            continue
        score = std_log(float(val))
        if len(heap) == k and score < heap[0][0]:
            continue
        heapq.heappush(heap, (score, i))
        if len(heap) > k:
            heapq.heappop(heap)
    heap.sort(key=lambda p: -p[0])
    return heap


class SigmoidTable:
    SIZE = 512
    MAX = 8

    def __init__(self) -> None:
        i = np.arange(self.SIZE + 1, dtype=np.float64)
        x = i * 2 * self.MAX / self.SIZE - self.MAX
        self.table = (1.0 / (1.0 + np.exp(-x))).astype(np.float32)

    def __call__(self, x: np.ndarray) -> np.ndarray:
        out = np.empty_like(x, dtype=np.float32)
        lo, hi = x < -self.MAX, x > self.MAX
        mid = ~(lo | hi)
        out[lo], out[hi] = 0.0, 1.0
        idx = ((x[mid] + self.MAX) * self.SIZE / self.MAX / 2).astype(np.int64)
        out[mid] = self.table[idx]
        return out


class Loss(abc.ABC):
    def __init__(self, wo: WeightMatrix) -> None:
        self.wo = wo
        self.sigmoid = SigmoidTable()

    def predict(
        self, k: int, threshold: float, hidden: np.ndarray
    ) -> list[tuple[float, int]]:
        output = self.compute_output(hidden)
        return top_k(k, threshold, output)

    @abc.abstractmethod
    def compute_output(self, hidden: np.ndarray) -> np.ndarray: ...


class BinaryLogisticLoss(Loss):
    def compute_output(self, hidden: np.ndarray) -> np.ndarray:
        return self.sigmoid(self.wo.dot_all(hidden))


class OneVsAllLoss(BinaryLogisticLoss):
    pass


class NegativeSamplingLoss(BinaryLogisticLoss):
    # Inference-time behavior of NS is identical to any binary-logistic loss;
    # the negative table is a training-only construct and is intentionally omitted.
    pass


class SoftmaxLoss(Loss):
    def compute_output(self, hidden: np.ndarray) -> np.ndarray:
        raw = self.wo.dot_all(hidden).astype(np.float64)
        e = np.exp(raw - raw.max())
        return (e / e.sum()).astype(np.float32)


class HierarchicalSoftmaxLoss(BinaryLogisticLoss):
    def __init__(self, wo: WeightMatrix, counts: Sequence[int]):
        super().__init__(wo)
        self.osz = len(counts)
        self.build_tree(counts)

    def build_tree(self, counts: Sequence[int]) -> None:
        osz = self.osz
        total = 2 * len(counts) - 1
        self.left = [-1] * total
        self.right = [-1] * total
        self.parent = [-1] * total
        count = [1e15] * total
        count[:osz] = counts

        leaf = osz - 1
        node = osz
        for i in range(osz, total):
            picks = []
            for _ in range(2):
                if leaf >= 0 and count[leaf] < count[node]:
                    picks.append(leaf)
                    leaf -= 1
                else:
                    picks.append(node)
                    node += 1
            a, b = picks
            self.left[i] = a
            self.right[i] = b
            count[i] = count[a] + count[b]
            self.parent[a] = self.parent[b] = i

    def predict(
        self, k: int, threshold: float, hidden: np.ndarray
    ) -> list[tuple[float, int]]:
        heap: list[tuple[float, int]] = []
        self.dfs(k, threshold, 2 * self.osz - 2, 0.0, heap, hidden)
        heap.sort(key=lambda p: -p[0])
        return heap

    def dfs(
        self,
        k: int,
        threshold: float,
        node: int,
        score: float,
        heap: list[tuple[float, int]],
        hidden: np.ndarray,
    ) -> None:
        if score < std_log(threshold) or (len(heap) == k and score < heap[0][0]):
            return

        left, right = self.left[node], self.right[node]
        if left == -1 and right == -1:
            heapq.heappush(heap, (score, node))
            if len(heap) > k:
                heapq.heappop(heap)
            return
        f = 1.0 / (1.0 + math.exp(-self.wo.dot_row(hidden, node - self.osz)))
        self.dfs(k, threshold, left, score + std_log(1.0 - f), heap, hidden)
        self.dfs(k, threshold, right, score + std_log(f), heap, hidden)


def build_loss(name: LossName, wo: WeightMatrix, target_counts: list[int]) -> Loss:
    match name:
        case LossName.HS:
            return HierarchicalSoftmaxLoss(wo, target_counts)
        case LossName.NS:
            return NegativeSamplingLoss(wo)
        case LossName.SOFTMAX:
            return SoftmaxLoss(wo)
        case LossName.OVA:
            return OneVsAllLoss(wo)
        case _:
            raise ValueError(f"Unknown loss: {name}")


# --------------------------------------------------------------------------------------
# FastText model
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Prediction:
    label: str
    score: float


class FastText:
    def __init__(self) -> None:
        self.args = Args()
        self.dictionary = Dictionary(self.args)
        self.input: WeightMatrix
        self.output: WeightMatrix
        self.loss: Loss
        self.quantized = False

    def load_model(self, path: str | os.PathLike[str]) -> None:
        buf = Path(path).read_bytes()
        r = Reader(buf)

        if r.i32() != FASTTEXT_MAGIC:
            raise ValueError(f"{path} has wrong file format!")
        version = r.i32()
        if version > FASTTEXT_VERSION:
            raise ValueError(f"{path} has wrong file format!")

        self.args = Args.load(r)
        if version == 11 and self.args.model is ModelName.SUP:
            self.args.maxn = 0  # old supervised models had no char ngrams

        self.dictionary = Dictionary.load(r, self.args)

        quant_input = r.bool()
        if quant_input:
            self.quantized = True
            self.input = QuantMatrix.load(r)
        else:
            self.input = DenseMatrix.load(r)

        if not quant_input and self.dictionary.is_pruned:
            raise ValueError(
                "Invalid model file. "
                "Please download the updated model from www.fasttext.cc. "
                "See issue #332 on Github for more information."
            )

        self.args.qout = r.bool()
        if self.quantized and self.args.qout:
            self.output = QuantMatrix.load(r)
        else:
            self.output = DenseMatrix.load(r)

        target_counts = self.dictionary.get_counts(
            EntryType.LABEL if self.args.model is ModelName.SUP else EntryType.WORD
        )
        self.loss = build_loss(self.args.loss, self.output, target_counts)

    def predict(
        self,
        text: str,
        k: int = 1,
        threshold: float = 0.0,
    ) -> tuple[Prediction, ...] | None:
        """Predicts the top-k labels for a given input string.

        Args:
            text: The input string to classify.
            k: The number of top labels to return. If -1, returns all labels.
            threshold: The minimum score threshold for labels to be included.

        Returns:
            A tuple of ``k`` predictions or ``None`` if no predictions met the
            threshold.
        """
        if self.args.model is not ModelName.SUP:
            raise ValueError("Model needs to be supervised for prediction!")

        # tokenize
        text = text.replace("\n", " ") + "\n"
        words, _ = self.dictionary.get_line(tokenize(text))
        if not words:
            return None
        k = self.dictionary.n_labels if k == -1 else k
        if k <= 0:
            raise ValueError("k needs to be >=1")

        # forward pass
        hidden = self.input.row_mean(words)
        heap = self.loss.predict(k, threshold, hidden)
        preds = [
            Prediction(
                label=self.dictionary.get_label(idx).decode("utf-8"),
                score=min(math.exp(score), 1.0),
            )
            for score, idx in heap
        ]
        return tuple(preds)


# --------------------------------------------------------------------------------------
# Model loading
# -------------------------------------------------------------------------------------


def download_model(quantized: bool = True, cache_dir: Path | None = None) -> Path:
    """Download and cache the pre-trained fastText language identification model."""

    versioned_path = Path(__file__).parent / "lid.176.ftz"
    if versioned_path.exists():
        return versioned_path

    if cache_dir is None:
        cache_dir = Path(
            os.getenv("FT_MODELS_DIR", Path.home() / ".cache" / "fasttext")
        ).expanduser()
    cache_dir.mkdir(parents=True, exist_ok=True)

    model_name = "lid.176.ftz" if quantized else "lid.176.bin"
    model_path = cache_dir / model_name
    if not model_path.exists():
        url = f"https://dl.fbaipublicfiles.com/fasttext/supervised-models/{model_name}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        with open(model_path, "wb") as f:
            f.write(response.content)
    return model_path


def load_model(
    path: str | os.PathLike[str] | None = None,
    *,
    quantized: bool = True,
) -> FastText:
    """Instantiates a FastText model and loads the pre-trained language identification
    checkpoint.

    Args:
        path: Path to the model file. If None, the model will be downloaded and cached.
        quantized: Whether to load the quantized model when no path is provided.

    See:
        https://fasttext.cc/docs/en/language-identification.html
    """
    path = path or download_model(quantized=quantized)
    model = FastText()
    model.load_model(path)
    return model
