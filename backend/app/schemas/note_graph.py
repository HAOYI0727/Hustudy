"""Bounded, metadata-only view of saved note links."""

from pydantic import BaseModel, Field

from .notes import NoteMetadata


class NoteGraphNode(NoteMetadata):
    incoming_count: int = Field(ge=0)
    outgoing_count: int = Field(ge=0)


class NoteGraphEdge(BaseModel):
    source_id: str
    target_id: str


class NoteGraph(BaseModel):
    course_id: str
    focus_note_id: str | None
    nodes: list[NoteGraphNode]
    edges: list[NoteGraphEdge]
    total_nodes: int = Field(ge=0)
    total_edges: int = Field(ge=0)
    node_limit: int
    edge_limit: int
    nodes_truncated: bool
    edges_truncated: bool
