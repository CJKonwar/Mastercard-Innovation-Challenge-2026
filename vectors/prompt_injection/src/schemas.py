"""Shared data types. Every other module speaks in these; nothing here imports from the project."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
import time
import uuid


class SurfaceType(str, Enum):
    """Where a payload is hidden."""
    REVIEW = "review"
    PRODUCT_DESC = "product_description"
    INVOICE_PDF = "invoice_pdf"
    EMAIL_RECEIPT = "email_receipt"
    MCP_TOOL_RESPONSE = "mcp_tool_response"
    RETURN_POLICY = "return_policy"


class TechniqueTier(str, Enum):
    """How the payload evades detection, escalating T0 to T5."""
    T0_NAIVE = "t0_naive_imperative"
    T1_AUTHORITY = "t1_authority_spoof"
    T2_OBFUSCATION = "t2_obfuscation"
    T3_SEMANTIC = "t3_semantic_lie"
    T4_MULTIHOP = "t4_multihop_split"
    T5_ADAPTIVE = "t5_adaptive"


class Objective(str, Enum):
    """Which unauthorised financial action the attacker wants."""
    PAYEE_SUBSTITUTION = "payee_substitution"
    GIFTCARD_INSERT = "giftcard_insert"
    CART_MANIPULATION = "cart_manipulation"
    PAYMENT_DOWNGRADE = "payment_downgrade"
    TOKEN_EXFIL = "token_exfil"
    BUDGET_ESCALATION = "budget_escalation"
    REFUND_REDIRECT = "refund_redirect"
    MERCHANT_SUBSTITUTION = "merchant_substitution"


ArchiveDescriptor = tuple[SurfaceType, TechniqueTier, Objective]


class Provenance(str, Enum):
    """Whether content came from a trusted source or an untrusted one."""
    TRUSTED = "trusted"
    UNTRUSTED = "untrusted"


class CapabilityClass(str, Enum):
    """How much damage a tool can do; gates how harshly it is judged."""
    READ = "read"
    WRITE = "write"
    FINANCIAL = "financial"


@dataclass
class Payload:
    """One attack: the injected text plus the cell it occupies in the archive."""
    text: str
    surface: SurfaceType
    technique: TechniqueTier
    objective: Objective
    target_spec: dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[str] = None
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    @property
    def descriptor(self) -> ArchiveDescriptor:
        """The archive cell this payload belongs to."""
        return (self.surface, self.technique, self.objective)


@dataclass
class Artifact:
    """A piece of content the agent reads, tagged with where it came from."""
    content: str
    surface: SurfaceType
    provenance: Provenance = Provenance.UNTRUSTED
    source_id: str = field(default_factory=lambda: "src_" + uuid.uuid4().hex[:8])
    payload_id: Optional[str] = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SourceNode:
    """An ingested source, recorded on the trace so provenance can be reconstructed."""
    source_id: str
    provenance: Provenance
    surface: Optional[SurfaceType]
    content: str
    payload_id: Optional[str] = None


@dataclass
class ToolCall:
    """One tool invocation, carrying the sources its arguments were derived from."""
    tool_name: str
    capability: CapabilityClass
    args: dict[str, Any]
    turn: int
    tainted_by: list[str] = field(default_factory=list)
    result: Any = None
    call_id: str = field(default_factory=lambda: "call_" + uuid.uuid4().hex[:8])


@dataclass
class ActionRecord:
    """A state change that actually happened, as recorded by the mock tools."""
    kind: str
    detail: dict[str, Any]
    turn: int
    caused_by_call: Optional[str] = None


@dataclass
class Trace:
    """Everything that happened during one agent run."""
    task_id: str
    user_instruction: str
    delegated_scope: dict[str, Any] = field(default_factory=dict)
    sources: list[SourceNode] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    actions: list[ActionRecord] = field(default_factory=list)
    final_state: dict[str, Any] = field(default_factory=dict)
    is_attack: bool = False
    payload_id: Optional[str] = None
    started_at: float = field(default_factory=time.time)

    def financial_calls(self) -> list[ToolCall]:
        """Just the money-moving calls."""
        return [c for c in self.tool_calls if c.capability is CapabilityClass.FINANCIAL]

    def source(self, sid: str) -> Optional[SourceNode]:
        """Look up an ingested source by id."""
        return next((s for s in self.sources if s.source_id == sid), None)


@dataclass
class OutcomeVerdict:
    """The judge's ruling on whether an attack succeeded."""
    success: bool
    matched_objective: Optional[Objective]
    detail: str = ""


class Policy(str, Enum):
    """What the Blue Team decides to do about an action."""
    ALLOW = "allow"
    STEP_UP = "step_up"
    BLOCK = "block"


@dataclass
class DetectorVerdict:
    """The Blue Team's per-tier scores, fused risk, and resulting policy."""
    p_content: float = 0.0
    p_graph: float = 0.0
    p_intent: float = 0.0
    risk: float = 0.0
    policy: Policy = Policy.ALLOW
    explain: dict[str, Any] = field(default_factory=dict)
