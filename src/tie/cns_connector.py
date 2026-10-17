"""Optional connector to CNS (``cns.gate``): binding only.

TIE is independent. It has no runtime dependency, imports nothing from CNS when
it loads, and its whole suite passes with CNS absent. This module is the one
place that knows CNS exists, and it asks for CNS only when a function that
needs it is called. Without CNS installed those calls raise
:class:`CnsNotInstalled` with the install command; nothing else in TIE is
affected, and the ``*_content`` functions work without CNS at all.

What connecting means
---------------------
CNS's shared gate contract carries, on every verdict, the subject it judged and
a digest of the content it judged (``GateResult.subject``,
``GateResult.subject_digest``). This module lets a TIE output be named that
way, so a verdict some other repository issued about a package can be checked
against exactly that package with ``GateResult.binds``.

That is all it does. TIE does not judge: it preserves before it interprets, and
its handoff is data, not execution. So there is no gate here, no verdict
mapping and no chain. Whether a package is good enough for anything is not
TIE's question and this module does not answer it.

What is bound
-------------
* :func:`package_content` is a whole ``TIEPackage``: its id, the source (id,
  media type, title, provenance, and a SHA-256 of the content with its length,
  not the transcript itself), the coverage segments with their checksums and
  statuses, every evidence record, artifact, identity reference and
  relationship, the reconstruction, the validation result, the knowledge views,
  the typed handoff, the routing signal and the build classification. Every
  dataclass field is bound, including any added later.
* :func:`handoff_content` is a ``TypedHandoff`` on its own.

Plain data only: enums become their values, tuples become lists, mappings keep
string keys, sets are sorted. Nothing volatile or process-local is bound (TIE
records no clocks and no object identities), so the same package built twice
digests the same.

Install with the extra: ``pip install 'tie-transcript-intelligence-engine[cns]'``.
"""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import importlib
import math
from collections.abc import Mapping
from types import ModuleType
from typing import Any, Optional

from tie.models import SourceRecord, TIEPackage, TypedHandoff

__all__ = [
    "CnsNotInstalled",
    "HANDOFF_SUBJECT",
    "PACKAGE_SUBJECT",
    "binds",
    "cns_available",
    "handoff_content",
    "handoff_digest",
    "package_content",
    "package_digest",
]

INSTALL_HINT = "pip install 'tie-transcript-intelligence-engine[cns]'"

PACKAGE_SUBJECT = "tie.package"
HANDOFF_SUBJECT = "tie.handoff"


class CnsNotInstalled(ImportError):
    """Raised by this module's functions when ``cns`` cannot be imported."""


def _cns_gate() -> ModuleType:
    """Import ``cns.gate`` on demand, or say exactly what is missing."""
    try:
        return importlib.import_module("cns.gate")
    except ImportError as exc:
        raise CnsNotInstalled(
            "tie.cns_connector needs the CNS package (cns.gate), which is not "
            f"installed. Install it with: {INSTALL_HINT}. TIE itself works "
            "without it."
        ) from exc


def cns_available() -> bool:
    """Whether the CNS gate contract can be imported in this environment."""
    try:
        _cns_gate()
    except CnsNotInstalled:
        return False
    return True


def _source_plain(source: SourceRecord) -> dict:
    """A source record with its text replaced by a hash and a length."""
    content = source.content
    plain = {
        f.name: _plain(getattr(source, f.name))
        for f in dataclasses.fields(source)
        if f.name != "content"
    }
    if content is None:
        plain["content_sha256"] = None
        plain["content_length"] = None
    elif isinstance(content, str):
        plain["content_sha256"] = hashlib.sha256(content.encode("utf-8", "surrogatepass")).hexdigest()
        plain["content_length"] = len(content)
    else:
        raise TypeError(f"source content must be a string; got {type(content).__name__}")
    return plain


def _plain(value: Any) -> Any:
    """Restrict a TIE value to the types ``cns.gate.subject_digest`` accepts."""
    if isinstance(value, enum.Enum):  # before str and int: TIE's enums are str mixins
        return _plain(value.value)
    if isinstance(value, SourceRecord):
        return _source_plain(value)
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: _plain(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise TypeError("cannot bind a verdict to NaN or an infinity")
        return value
    if isinstance(value, Mapping):
        if not all(isinstance(k, str) for k in value):
            raise TypeError("mapping keys must be strings to be bound")
        return {k: _plain(value[k]) for k in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, (set, frozenset)):
        items = [_plain(v) for v in value]
        try:
            return sorted(items)
        except TypeError:  # mixed kinds have no natural order; fall back to a stable one
            return sorted(items, key=repr)
    raise TypeError(f"cannot bind a verdict to {type(value).__name__}")


def _require(obj: object, kind: type, what: str) -> None:
    if not isinstance(obj, kind):
        raise TypeError(f"{what} is expected here; got {type(obj).__name__}")


def package_content(package: TIEPackage) -> dict:
    """The content a verdict on ``package`` is bound to (plain data, no CNS needed)."""
    _require(package, TIEPackage, "a TIEPackage")
    return _plain(package)


def handoff_content(handoff: TypedHandoff) -> dict:
    """The content a verdict on ``handoff`` is bound to (plain data, no CNS needed)."""
    _require(handoff, TypedHandoff, "a TypedHandoff")
    return _plain(handoff)


def package_digest(package: TIEPackage) -> str:
    """The digest a verdict bound to ``package`` carries, with ``PACKAGE_SUBJECT``."""
    content = package_content(package)
    return _cns_gate().subject_digest(content)


def handoff_digest(handoff: TypedHandoff) -> str:
    """The digest a verdict bound to ``handoff`` carries, with ``HANDOFF_SUBJECT``."""
    content = handoff_content(handoff)
    return _cns_gate().subject_digest(content)


def binds(result: object, obj: object, *, subject: Optional[str] = None) -> bool:
    """Whether ``result`` is a CNS verdict issued against exactly ``obj``.

    ``obj`` is a ``TIEPackage`` (default subject ``PACKAGE_SUBJECT``) or a
    ``TypedHandoff`` (default ``HANDOFF_SUBJECT``). An unbound or hand-built
    result, anything that is not a ``cns.gate.GateResult``, a different
    subject label, or a verdict about different content is ``False``.
    """
    if isinstance(obj, TIEPackage):
        label, digest = PACKAGE_SUBJECT, package_digest
    elif isinstance(obj, TypedHandoff):
        label, digest = HANDOFF_SUBJECT, handoff_digest
    else:
        raise TypeError(f"a TIEPackage or a TypedHandoff is expected here; got {type(obj).__name__}")
    computed = digest(obj)
    if not isinstance(result, _cns_gate().GateResult):
        return False
    return bool(result.binds(label if subject is None else subject, computed))
