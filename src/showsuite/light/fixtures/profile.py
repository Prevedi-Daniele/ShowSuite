"""Profili fixture, istanze e patch."""
from __future__ import annotations

from dataclasses import dataclass, field

from ..dmx.universe import DMX_CHANNELS


@dataclass(frozen=True)
class ChannelDef:
    name: str            # es. "Dimmer", "Red", "Pan"
    default: int = 0     # valore a riposo (0-255, o 0-65535 se fine=True)
    fine: bool = False   # occupa 2 canali (16 bit, MSB poi LSB)

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

    def offset_of(self, name: str) -> int:
        """Offset (0-based) del primo canale con quel nome."""
        off = 0
        for c in self.channels:
            if c.name == name:
                return off
            off += c.width
        raise KeyError(name)


def generic_dimmer() -> FixtureProfile:
    return FixtureProfile("Generic", "Dimmer", "1ch", (ChannelDef("Dimmer"),))


def generic_rgb() -> FixtureProfile:
    return FixtureProfile("Generic", "RGB", "3ch",
                          (ChannelDef("Red"), ChannelDef("Green"), ChannelDef("Blue")))


@dataclass
class FixtureInstance:
    name: str
    profile: FixtureProfile
    universe: int
    address: int  # 1-512

    @property
    def end_address(self) -> int:
        return self.address + self.profile.footprint - 1

    def write(self, values: dict[str, int], target) -> None:
        """Scrive i valori (per nome canale) in `target` (un Universe)."""
        for name, v in values.items():
            base = self.address + self.profile.offset_of(name)
            ch = next(c for c in self.profile.channels if c.name == name)
            if ch.fine:
                v = max(0, min(65535, int(v)))
                target.set(base, v >> 8)
                target.set(base + 1, v & 0xFF)
            else:
                target.set(base, v)


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
