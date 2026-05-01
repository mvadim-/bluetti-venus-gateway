from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PollSpec:
    name: str
    addr: int
    length: int
    every: int

    def due_on(self, cycle: int) -> bool:
        return self.every > 0 and cycle % self.every == 0


def build_poll_profile(
    profile: str,
    *,
    enable_pv: bool = False,
    enable_pack_diagnostics: bool = False,
) -> list[PollSpec]:
    if profile != "vrm-minimal":
        raise ValueError(f"unsupported poll profile: {profile}")

    specs = [
        PollSpec("home", 100, 92, 1),
        PollSpec("grid", 1300, 19, 1),
        PollSpec("load", 1400, 36, 1),
        PollSpec("inverter", 1500, 15, 2),
    ]
    if enable_pv:
        specs.append(PollSpec("pv", 1200, 42, 1))
    if enable_pack_diagnostics:
        specs.extend(
            [
                PollSpec("packMain", 6000, 42, 2),
                PollSpec("packItem", 6100, 104, 5),
            ]
        )
    return specs


def due_polls(specs: list[PollSpec], cycle: int) -> list[PollSpec]:
    return [spec for spec in specs if spec.due_on(cycle)]

