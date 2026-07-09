"""Interactive user input."""
# pylint: disable=unnecessary-ellipsis,unused-argument

from typing import Protocol

from usdx_dl import ansi


class Prompt(Protocol):
    """Interactive prompts for user input."""

    def string(
        self,
        prompt: str,
        *,
        default: str | None = None,
        description: str | None = None,
    ) -> str:
        """Single-line string input."""
        ...

    def multiline(
        self,
        prompt: str,
        *,
        default: str | None = None,
        description: str | None = None,
    ) -> str:
        """Multi-line string input."""
        ...

    def yes_no(
        self,
        prompt: str,
        *,
        default: bool | None = None,
        description: str | None = None,
    ) -> bool:
        """Yes/no input."""
        ...

    def choice(
        self,
        prompt: str,
        *,
        choices: list[str],
        default: int | None = None,
        description: str | None = None,
    ) -> int:
        """Multiple-choice input. Returns the index of the selected choice."""
        ...


class NonInteractivePrompt:
    """Non-interactive prompt that always returns defaults."""

    def string(
        self,
        prompt: str,
        *,
        default: str | None = None,
        description: str | None = None,
    ) -> str:
        """Single-line string input."""
        return default or ""

    def multiline(
        self,
        prompt: str,
        *,
        default: str | None = None,
        description: str | None = None,
    ) -> str:
        """Multi-line string input."""
        return default or ""

    def yes_no(
        self,
        prompt: str,
        *,
        default: bool | None = None,
        description: str | None = None,
    ) -> bool:
        """Yes/no input."""
        return default if default is not None else False

    def choice(
        self,
        prompt: str,
        *,
        choices: list[str],
        default: int | None = None,
        description: str | None = None,
    ) -> int:
        """Multiple-choice input."""
        return default if default is not None else 0


class CliPrompt:
    """Command-line implementation of Prompt."""

    @staticmethod
    def string(
        prompt: str,
        *,
        default: str | None = None,
        description: str | None = None,
    ) -> str:
        """Single-line string input."""
        if description is not None:
            prompt += f" {ansi.DIM}({description}){ansi.RESET}"
        if default is not None:
            prompt += f" [{ansi.BOLD}{default}{ansi.RESET}]"
        prompt += ": "
        result = input(prompt)
        return result or default or ""

    @staticmethod
    def multiline(
        prompt: str,
        *,
        default: str | None = None,
        description: str | None = None,
    ) -> str:
        """Multi-line string input."""
        if description is not None:
            prompt += f" {ansi.DIM}({description}){ansi.RESET}"
        if default is not None:
            if "\n" not in default:
                prompt += f" [{ansi.BOLD}{default}{ansi.RESET}]"
            else:
                prompt += f"\n{ansi.DIM}[{default}]{ansi.RESET}"
        prompt += f"\n{ansi.DIM}[end with two empty lines]{ansi.RESET}"
        print(prompt)
        lines: list[str] = []
        while True:
            line = input()
            if not line and len(lines) > 0 and not lines[-1]:
                break
            lines.append(line)
        result = "\n".join(lines)
        return result or default or ""

    @staticmethod
    def yes_no(
        prompt: str,
        *,
        default: bool | None = None,
        description: str | None = None,
    ) -> bool:
        """Yes/no input."""
        if description is not None:
            prompt += f" {ansi.DIM}({description}){ansi.RESET}"
        if default is not None:
            choices = (
                f"{ansi.BOLD}Y{ansi.RESET}/n"
                if default
                else f"y/{ansi.BOLD}N{ansi.RESET}"
            )
            prompt += f" [{choices}]"
        prompt += ": "
        while True:
            result = input(prompt).strip().lower()
            if not result and default is not None:
                return default
            if result in ("y", "yes"):
                return True
            if result in ("n", "no"):
                return False

    @staticmethod
    def choice(
        prompt: str,
        *,
        choices: list[str],
        default: int | None = None,
        description: str | None = None,
    ) -> int:
        """Multiple-choice input."""
        if not choices:
            raise ValueError("Choices list cannot be empty.")
        if default is not None and not 0 <= default < len(choices):
            raise ValueError("Default index is out of range of choices.")
        if description is not None:
            prompt += f"\n{ansi.DIM}{description}{ansi.RESET}"
        for i, choice in enumerate(choices):
            prompt += f"\n  [{ansi.BLUE}{i + 1}{ansi.RESET}] {choice}"
        choose_prompt = f"Choice (1-{len(choices)})"
        if default is not None:
            choose_prompt += f" [{ansi.BOLD}{default + 1}{ansi.RESET}]"
        choose_prompt += ": "
        print(prompt)
        while True:
            result = input(choose_prompt).strip()
            if not result and default is not None:
                return default
            if result.isdigit() and 1 <= (idx := int(result)) <= len(choices):
                return idx - 1
            print(
                f"{ansi.RED}Error: Invalid choice. Please enter a number between "
                f"1 and {len(choices)}.{ansi.RESET}"
            )
