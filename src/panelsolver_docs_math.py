"""MkDocs extension that renders LaTeX to self-contained MathML at build time."""

from __future__ import annotations

from latex2mathml.converter import convert
from markdown import Markdown
from markdown.extensions import Extension
from markdown.inlinepatterns import InlineProcessor
from markdown.preprocessors import Preprocessor


def _mathml(latex: str, *, display: str) -> str:
    try:
        return convert(latex.strip(), display=display)
    except Exception as exc:
        preview = " ".join(latex.strip().split())[:120]
        raise RuntimeError(
            f"Could not render documentation math {preview!r}: {exc}"
        ) from exc


class _MathFencePreprocessor(Preprocessor):
    def run(self, lines: list[str]) -> list[str]:
        rendered: list[str] = []
        index = 0
        while index < len(lines):
            if lines[index].strip() != "```math":
                rendered.append(lines[index])
                index += 1
                continue
            start = index + 1
            index = start
            while index < len(lines) and lines[index].strip() != "```":
                index += 1
            if index == len(lines):
                raise RuntimeError(f"Unclosed documentation math fence at line {start}")
            rendered.extend(
                ("", _mathml("\n".join(lines[start:index]), display="block"), "")
            )
            index += 1
        return rendered


class _InlineMathProcessor(InlineProcessor):
    def handleMatch(self, match, data):
        del data
        mathml = _mathml(match.group(1), display="inline")
        placeholder = self.md.htmlStash.store(mathml)
        return placeholder, match.start(0), match.end(0)


class OfflineMathExtension(Extension):
    def extendMarkdown(self, md: Markdown) -> None:
        md.preprocessors.register(_MathFencePreprocessor(md), "offline_math_fence", 30)
        md.inlinePatterns.register(
            _InlineMathProcessor(r"(?<!\\)\$(?!\$)(.+?)(?<!\\)\$", md),
            "offline_inline_math",
            185,
        )


def makeExtension(**kwargs) -> OfflineMathExtension:
    return OfflineMathExtension(**kwargs)
