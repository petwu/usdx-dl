"""Estimate FLOPS (floating point operations per second) for CPU/GPU using PyTorch."""

import math
from time import perf_counter
from typing import TYPE_CHECKING

import torch

from usdx_dl import ansi


def measure(
    device: str | torch.device,
    duration: float = 1.0,
    shape: tuple[int, ...] = (2, 768, 2048),
) -> float:
    """Estimate FLOPS using large matrix multiplication via PyTorch.

    Args:
        device: The device to run the test on, either CPU or any
            pytorch-supported accelerator.
        duration: How long to run the test in seconds.
        shape: The shape of the matrices to multiply.
    """
    if isinstance(device, str):
        device = torch.device(device)
    assert len(shape) >= 2, "Shape must have at least 2 dimensions."
    assert math.prod(shape) > 1e6, (
        "Shape must have at least 10^6 elements so the python overhead "
        "is negligible and we only measure the torch matmul performance."
    )
    batch_dims = shape[:-2]
    M = N = shape[-2]
    K = shape[-1]
    x = torch.randn((*batch_dims, M, K), dtype=torch.float32, device=device)
    y = torch.randn((*batch_dims, K, N), dtype=torch.float32, device=device)

    # warmup
    for _ in range(5):
        torch.matmul(x, y)
    if device.type != "cpu":
        torch.accelerator.synchronize()

    # benchmark
    start = perf_counter()
    num_iters = 0
    while perf_counter() - start < duration:
        torch.matmul(x, y)
        num_iters += 1
        if device.type != "cpu":
            torch.accelerator.synchronize()
    elapsed_time = perf_counter() - start

    # calculate FLOPS
    # For two matrices of shape (M, K) and (K, N), the result has M*N elements with
    # each element requiring K multiplications and K-1 additions, so the total number
    # of operations is
    #   M * N * (2K - 1) = 2 * M * N * K
    # Batch dimensions are just multiplicative factors:
    #   2 * \prod B_i * M * N * K
    B = math.prod(batch_dims)
    ops_per_matmul = 2 * B * M * N * K
    flops = (ops_per_matmul * num_iters) / elapsed_time

    return flops


def cpu(duration: float = 1.0) -> float:
    """Estimate CPU FLOPS using large matrix multiplication."""
    device = torch.device("cpu")
    return measure(device, duration)


def gpu(duration: float = 1.0) -> float | None:
    """Estimate GPU FLOPS using large matrix multiplication via PyTorch."""
    device = torch.accelerator.current_accelerator()
    if not device:
        return None

    return measure(device, duration)


def fmt(flops: float, decimals: int = 2) -> str:
    """Format FLOPS as a human-readable string."""
    if flops < 0:
        return "N/A"
    # cSpell: disable-next-line
    units = ["FLOPS", "KFLOPS", "MFLOPS", "GFLOPS", "TFLOPS", "PFLOPS"]
    for unit in units:
        if flops < 1000:
            return f"{flops:.{decimals}f} {unit}"
        flops /= 1000
    return f"{flops:.{decimals}e} FLOPS"


# provide lazy-set attributes for CPU and GPU FLOPS for easy access that doesn't
# require a fresh measurement
if TYPE_CHECKING:
    CPU: float
    GPU: float | None


def __getattr__(name: str) -> float | None:
    if name == "CPU":
        if "CPU" not in globals():
            globals()["CPU"] = cpu()
        return globals()["CPU"]
    if name == "GPU":
        if "GPU" not in globals():
            globals()["GPU"] = gpu()
        return globals()["GPU"]
    raise AttributeError(f"module {__name__} has no attribute {name}")


if __name__ == "__main__":
    print(f"{ansi.BOLD}FLOPS Benchmark{ansi.RESET}")
    print(f"{ansi.DIM}CPU...{ansi.RESET}", end="", flush=True)
    cpu_flops = cpu()
    print(f"\r{ansi.CYAN}CPU: {fmt(cpu_flops)}{ansi.RESET}")
    print(f"{ansi.DIM}GPU...{ansi.RESET}", end="", flush=True)
    if gpu_flops := gpu():
        print(f"\r{ansi.MAGENTA}GPU: {fmt(gpu_flops)}{ansi.RESET}")
    else:
        print(f"\r{ansi.YELLOW}GPU: N/A{ansi.RESET}")
