"""HiggsLab hosted and local evaluation primitives."""

from .submission import Submission, SubmissionError, parse_submission

__all__ = ["Submission", "SubmissionError", "parse_submission"]
