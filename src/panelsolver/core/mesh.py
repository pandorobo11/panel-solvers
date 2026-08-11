"""Topology-preserving contracts for already-resolved panel meshes."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

import numpy as np

from ._validation import (
    float_array,
    freeze_payload,
    index_array,
    integer_scalar,
    nonempty_text,
    require_nonempty_faces,
)
from .contracts import PanelGeometry, PayloadValue
from .errors import ContractValueError


@dataclass(frozen=True, slots=True)
class MeshComponent:
    """Stable identity and uninterpreted source metadata for one component."""

    component_id: int
    source: str
    metadata: Mapping[str, PayloadValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "component_id",
            integer_scalar(
                self.component_id,
                field="MeshComponent.component_id",
                nonnegative=True,
            ),
        )
        object.__setattr__(
            self,
            "source",
            nonempty_text(self.source, field="MeshComponent.source"),
        )
        object.__setattr__(
            self,
            "metadata",
            freeze_payload(self.metadata, field="MeshComponent.metadata"),
        )


@dataclass(frozen=True, slots=True, eq=False)
class PanelMesh:
    """Immutable topology aligned with an already-validated ``PanelGeometry``.

    This contract validates array ownership, indexing, and alignment only. It
    deliberately does not load files, repair winding, reject repeated triangle
    indices, derive normals/areas, or select a mesh strictness policy.
    """

    vertices_stl_m: np.ndarray
    faces: np.ndarray
    geometry: PanelGeometry
    components: tuple[MeshComponent, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.geometry, PanelGeometry):
            raise ContractValueError(
                "PanelMesh.geometry",
                "must be a PanelGeometry instance",
            )

        vertices = float_array(
            self.vertices_stl_m,
            field="PanelMesh.vertices_stl_m",
            shape=("n_vertices", 3),
        )
        if vertices.shape[0] == 0:
            raise ContractValueError(
                "PanelMesh.vertices_stl_m",
                "must contain at least one vertex",
            )

        faces = index_array(
            self.faces,
            field="PanelMesh.faces",
            shape=("n_faces", 3),
        )
        require_nonempty_faces(faces.shape[0], field="PanelMesh.faces")
        if faces.shape[0] != self.geometry.n_faces:
            raise ContractValueError(
                "PanelMesh.faces",
                "face count must match PanelGeometry",
            )
        if np.any(faces >= vertices.shape[0]):
            raise ContractValueError(
                "PanelMesh.faces",
                "vertex indices must be smaller than the vertex count",
            )

        try:
            components = tuple(self.components)
        except TypeError as exc:
            raise ContractValueError(
                "PanelMesh.components",
                "must be an iterable of MeshComponent instances",
            ) from exc
        if not components or not all(
            isinstance(component, MeshComponent) for component in components
        ):
            raise ContractValueError(
                "PanelMesh.components",
                "must contain MeshComponent instances",
            )

        by_id = {component.component_id: component for component in components}
        if len(by_id) != len(components):
            raise ContractValueError(
                "PanelMesh.components",
                "component_id values must be unique",
            )
        expected_ids = set(self.geometry.unique_component_ids)
        if set(by_id) != expected_ids:
            raise ContractValueError(
                "PanelMesh.components",
                f"component IDs must equal geometry component IDs {sorted(expected_ids)}",
            )

        object.__setattr__(self, "vertices_stl_m", vertices)
        object.__setattr__(self, "faces", faces)
        object.__setattr__(
            self,
            "components",
            tuple(by_id[component_id] for component_id in sorted(by_id)),
        )

    @property
    def n_vertices(self) -> int:
        return self.vertices_stl_m.shape[0]

    @property
    def n_faces(self) -> int:
        return self.faces.shape[0]

    @property
    def face_component_ids(self) -> np.ndarray:
        """Read-only component identity aligned one-to-one with ``faces``."""
        return self.geometry.component_ids


__all__ = ("MeshComponent", "PanelMesh")
