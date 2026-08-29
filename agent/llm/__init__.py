"""Shared low-level structured-completion plumbing for OpenAI adapters.

Each capability (classification, analysis) still owns its own provider class
(lazy client construction, its own Protocol, its own error mapping choices at
the call site), so tests can inject a fake client the same way for either.
This module only shares the one piece of logic that would otherwise be
duplicated verbatim: the SDK call, its exception mapping, and metadata
extraction.
"""
