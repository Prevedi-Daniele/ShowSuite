# ShowSuite

Professional Cross-Platform Show Control & DMX Lighting Suite.

ShowSuite unifies lighting control (inspired by modern DMX consoles) and live cue playback (sound, video, network, MIDI, timecode) into a single desktop application for live events, theater, concerts, and installations.

---

## Features

### QLab Show Control Engine
- **Hierarchical Cue List**: Groups (Timeline, Playlist, First/Advance, Random), pre-wait, post-wait, continue actions.
- **Audio & Matrix Mixer**: Multi-track playback, in/out trimming, pitch shifting, slices, non-destructive N×M matrix mixer (dB/linear) with timed fades.
- **Video & Stage Geometry**: Video playback, live camera capture, text projection, multi-screen mapping with perspective corner-pinning, edge blending, and grid warping.
- **Network & Show Control**: Full OSC dictionary, UDP, TCP, and RAW HEX byte stream transmission.
- **MIDI & MSC**: Note On/Off, Control Change, Program Change, Pitch Bend, and MIDI Show Control (MSC MMA RP-002).
- **Timecode Engine**: SMPTE 12M timecode (24, 25, 29.97 DF, 30 fps), MTC quarter-frame decoder, LTC audio decoder with zero-crossing detection, freewheeling chasing state machine, and frame-accurate cue triggers.

### Lightkey DMX Lighting Engine
- **DMX Universe Engine**: 4 universes (2048 DMX channels) running at up to 44 Hz refresh rate with Enttec DMX USB Pro / Open DMX support.
- **Fixture Profiles & Visualizer**: Extensive fixture library, visual stage layout with fixture selection, fan generator, and color/gobo/beam controls.
- **Palettes, Presets & Cue Engine**: 60 FPS cue transitions, crossfaders, and attribute isolation.
- **Effects Engine**: Waveform generators (Sine, Saw, Ramp, Square, Bezier), Pan/Tilt motion paths (Circle, Lissajous 8, Spiral), phase fanning, and Beat Clock with Tap Tempo.

### In-Process Integration
- **ShowSuite Bridge**: Zero-latency OSC routing between the QLab Cue Scheduler and the Lightkey lighting engine without requiring network loopback sockets.

---

## Getting Started

### Prerequisites
- Node.js (v18+)
- npm

### Installation
```bash
git clone https://github.com/your-username/ShowSuite.git
cd ShowSuite
npm install
```

### Development
Start the application in development mode with hot-reloading:
```bash
npm run dev
```

Run in standalone modes:
```bash
# Standalone Lighting mode
npm run start:lightkey

# Standalone Show Control mode
npm run start:qlab
```

### Running Tests
Execute the full test suite (14 test suites, 100% passing):
```bash
npm test
```

### Building & Packaging
Build the production web bundle:
```bash
npm run build
```

Package desktop installers:
```bash
# Windows (NSIS Installer + Portable .exe)
npm run package:win

# Linux (AppImage + .deb)
npm run package:linux
```

---

## Project Structure

```
ShowSuite/
├── src/
│   ├── core/           # Core engines (DMX, Fixtures, Control, QLab, Timecode, Effects)
│   ├── frontend-lightkey/  # React UI components for the Lighting Console
│   ├── frontend-qlab/      # React UI components for QLab Show Control
│   ├── shared/         # Common UI components, MacButton, ShowSuiteBridge
│   └── main/           # Electron main process and preload bridge
├── test/               # Unified test suites (14 suites) and test runner
├── public/             # Static web assets
├── build/              # Distribution icons and packaging assets
├── electron-builder.json # Packaging configuration for Windows and Linux
└── package.json        # Dependencies and build scripts
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
