"""Test rapido interfaccia DMX.

  python -m showsuite.light.tools.dmx_test opendmx /dev/ttyUSB0 [canale] [secondi]
  python -m showsuite.light.tools.dmx_test artnet 192.168.1.50

Fa lampeggiare il canale scelto (default 1) tra 0 e 255 ogni secondo.
Windows: usare COM3 ecc. al posto di /dev/ttyUSB0.
"""
from __future__ import annotations

import sys
import time

from ..dmx import Mixer, OutputManager
from ..project import OutputConfig


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    kind, target = argv[0], argv[1]
    channel = int(argv[2]) if len(argv) > 2 else 1
    seconds = float(argv[3]) if len(argv) > 3 else 10
    params = {"port": target} if kind == "opendmx" else {"host": target}
    cfg = OutputConfig(kind, 1, params)
    mixer = Mixer()
    layer = mixer.add_layer(1)
    om = OutputManager(mixer)
    om.route(1, cfg.build())
    om.start()
    print(f"Test {kind} su {target}, canale {channel}, {seconds:.0f}s. Ctrl+C per uscire.")
    end = time.time() + seconds
    try:
        while time.time() < end:
            for v in (255, 0):
                layer.set(1, channel, v)
                print("canale", channel, "=", v)
                time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        om.stop()
    for drv, err in om.errors[:3]:
        print("ERRORE:", type(drv).__name__, err)
    return 1 if om.errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
