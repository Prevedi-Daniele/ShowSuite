"""Profili fixture, istanze e patch."""
from __future__ import annotations

from dataclasses import dataclass, field

from ..dmx.universe import DMX_CHANNELS


@dataclass(frozen=True)
class ChannelDef:
    name: str            # es. "Dimmer", "Red", "Pan"
    default: int = 0     # valore a riposo (0-255, o 0-65535 se fine=True)
    fine: bool = False   # occupa 2 canali (16 bit, MSB poi LSB)
    kind: str = ""       # "intensity" | "red" | "green" | "blue" | "white" | "amber" | "uv" | ""

    @property
    def width(self) -> int:
        return 2 if self.fine else 1


@dataclass(frozen=True)
class FixtureProfile:
    manufacturer: str
    model: str
    mode: str
    channels: tuple[ChannelDef, ...]

    @property
    def footprint(self) -> int:
        return sum(c.width for c in self.channels)

    @property
    def is_mover(self) -> bool:
        return any(c.name.lower().startswith(("pan", "tilt")) for c in self.channels)

    def channel_of_kind(self, kind: str) -> ChannelDef | None:
        return next((c for c in self.channels if c.kind == kind), None)

    def offset_of(self, name: str) -> int:
        """Offset (0-based) del primo canale con quel nome."""
        off = 0
        for c in self.channels:
            if c.name == name:
                return off
            off += c.width
        raise KeyError(name)


def generic_dimmer() -> FixtureProfile:
    return FixtureProfile("Generic", "Dimmer", "1ch", (ChannelDef("Dimmer", kind="intensity"),))


def generic_rgb() -> FixtureProfile:
    return FixtureProfile("Generic", "RGB", "3ch",
                          (ChannelDef("Red", kind="red"), ChannelDef("Green", kind="green"),
                           ChannelDef("Blue", kind="blue")))


@dataclass
class FixtureInstance:
    name: str
    profile: FixtureProfile
    universe: int
    address: int  # 1-512
    x: float = 0.5  # posizione nel Preview (0-1)
    y: float = 0.5
    rotation: float = 0.0     # gradi: 0 = beam verso il basso, positivo = antiorario
    beam_angle: float = 30.0  # apertura del cono (gradi)
    hide_beam: bool = False

    @property
    def end_address(self) -> int:
        return self.address + self.profile.footprint - 1

    def channel_values(self, values: dict[str, int]) -> dict[int, int]:
        """Converte {nome canale: valore} in {canale DMX: 0-255}."""
        out: dict[int, int] = {}
        for name, v in values.items():
            base = self.address + self.profile.offset_of(name)
            ch = next(c for c in self.profile.channels if c.name == name)
            if ch.fine:
                v = max(0, min(65535, int(v)))
                out[base], out[base + 1] = v >> 8, v & 0xFF
            else:
                out[base] = max(0, min(255, int(v)))
        return out

    def write(self, values: dict[str, int], target) -> None:
        """Scrive i valori (per nome canale) in `target` (un Universe)."""
        for ch, v in self.channel_values(values).items():
            target.set(ch, v)


class PatchError(ValueError):
    pass


@dataclass
class Patch:
    fixtures: list[FixtureInstance] = field(default_factory=list)

    def add(self, fx: FixtureInstance) -> FixtureInstance:
        if fx.address < 1 or fx.end_address > DMX_CHANNELS:
            raise PatchError(f"{fx.name}: indirizzi {fx.address}-{fx.end_address} fuori universo")
        for o in self.fixtures:
            if o.universe == fx.universe and fx.address <= o.end_address and o.address <= fx.end_address:
                raise PatchError(f"{fx.name} si sovrappone a {o.name} nell'universo {fx.universe}")
        self.fixtures.append(fx)
        return fx

    def remove(self, name: str) -> None:
        self.fixtures = [f for f in self.fixtures if f.name != name]

    def find(self, name: str) -> FixtureInstance:
        for f in self.fixtures:
            if f.name == name:
                return f
        raise KeyError(name)

    def next_free(self, universe: int, footprint: int) -> int | None:
        """Primo indirizzo libero che ospita `footprint` canali."""
        used = sorted((f.address, f.end_address) for f in self.fixtures if f.universe == universe)
        addr = 1
        for s, e in used:
            if addr + footprint - 1 < s:
                break
            addr = max(addr, e + 1)
        return addr if addr + footprint - 1 <= DMX_CHANNELS else None
