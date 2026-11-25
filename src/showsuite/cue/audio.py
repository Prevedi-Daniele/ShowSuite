"""Motore audio dei cue: riproduzione con slice/loop/rate, matrice di mixaggio, envelope, EQ, delay, panic, duck.

Richiede numpy (+ scipy per l'EQ, soundfile per leggere i file). La riproduzione su scheda audio usa `sounddevice`
(opzionale, NON provata su hardware): senza, `AudioMixer.render` produce i blocchi per rendering offline/test.
Approssimazioni dichiarate: preserve pitch non implementato (rate cambia anche il tono); effetti = EQ parametrico,
filtri passa-alto/basso, delay; niente plugin AudioUnit/VST; stop "soft" = taglio immediato (senza coda effetti)."""
from __future__ import annotations

import math

import numpy as np

from .engine import ActionHandler, CueState, Runtime
from .model import TYPE_AUDIO, TYPE_VIDEO, Cue
from .playback import INFINITE, PlaybackPlan


def db_to_gain(value: float) -> float:
    if value <= -200.0:
        return 0.0
    return 10.0 ** (value / 20.0)


def envelope_value(points: list, time_value: float) -> float:
    """Envelope integrato: lista di [secondi, dB] interpolata linearmente in dB. Vuota = 0 dB."""
    if len(points) == 0:
        return 0.0
    ordered = sorted(points, key=lambda item: item[0])
    if time_value <= ordered[0][0]:
        return float(ordered[0][1])
    for index in range(len(ordered) - 1):
        left, right = ordered[index], ordered[index + 1]
        if left[0] <= time_value <= right[0]:
            if right[0] == left[0]:
                return float(right[1])
            fraction = (time_value - left[0]) / (right[0] - left[0])
            return float(left[1]) + (float(right[1]) - float(left[1])) * fraction
    return float(ordered[-1][1])


def biquad_coefficients(kind: str, frequency: float, gain_db: float, q: float, sample_rate: float):
    """Coefficienti RBJ (b, a) per peak, lowshelf, highshelf, lowpass, highpass."""
    omega = 2.0 * math.pi * frequency / sample_rate
    alpha = math.sin(omega) / (2.0 * max(q, 0.05))
    cosine = math.cos(omega)
    amplitude = 10.0 ** (gain_db / 40.0)
    if kind == "peak":
        b = [1 + alpha * amplitude, -2 * cosine, 1 - alpha * amplitude]
        a = [1 + alpha / amplitude, -2 * cosine, 1 - alpha / amplitude]
    elif kind == "lowshelf":
        root = 2 * math.sqrt(amplitude) * alpha
        b = [amplitude * ((amplitude + 1) - (amplitude - 1) * cosine + root),
             2 * amplitude * ((amplitude - 1) - (amplitude + 1) * cosine),
             amplitude * ((amplitude + 1) - (amplitude - 1) * cosine - root)]
        a = [(amplitude + 1) + (amplitude - 1) * cosine + root, -2 * ((amplitude - 1) + (amplitude + 1) * cosine),
             (amplitude + 1) + (amplitude - 1) * cosine - root]
    elif kind == "highshelf":
        root = 2 * math.sqrt(amplitude) * alpha
        b = [amplitude * ((amplitude + 1) + (amplitude - 1) * cosine + root),
             -2 * amplitude * ((amplitude - 1) + (amplitude + 1) * cosine),
             amplitude * ((amplitude + 1) + (amplitude - 1) * cosine - root)]
        a = [(amplitude + 1) - (amplitude - 1) * cosine + root, 2 * ((amplitude - 1) - (amplitude + 1) * cosine),
             (amplitude + 1) - (amplitude - 1) * cosine - root]
    elif kind == "lowpass":
        b = [(1 - cosine) / 2, 1 - cosine, (1 - cosine) / 2]
        a = [1 + alpha, -2 * cosine, 1 - alpha]
    elif kind == "highpass":
        b = [(1 + cosine) / 2, -(1 + cosine), (1 + cosine) / 2]
        a = [1 + alpha, -2 * cosine, 1 - alpha]
    else:
        raise ValueError("tipo di banda EQ sconosciuto: " + kind)
    return np.array(b) / a[0], np.array(a) / a[0]


class Voice:
    def __init__(self, state: CueState, data: np.ndarray, file_rate: int, plan: PlaybackPlan, channels_out: int):
        self.state = state
        self.data = data
        self.file_rate = file_rate
        self.plan = plan
        self.time = 0.0
        self.matrix_previous: np.ndarray | None = None
        self.filters: list = []
        self.filter_state: dict = {}
        self.delay_buffers: dict = {}
        self.finished = False
        self.ending = False


class AudioMixer(ActionHandler):
    def __init__(self, runtime: Runtime, sample_rate: int = 48000, output_channels: int = 2, block_size: int = 512):
        self.runtime = runtime
        self.sample_rate = sample_rate
        self.output_channels = output_channels
        self.block_size = block_size
        self.voices: dict[str, Voice] = {}
        self.cache: dict[str, tuple] = {}
        self.stream = None

    def install(self) -> None:
        self.runtime.register_handler(TYPE_AUDIO, self)
        self.runtime.register_handler(TYPE_VIDEO, self)

    # --- handler ---
    def _load(self, path: str):
        if path not in self.cache:
            import soundfile
            data, rate = soundfile.read(path, dtype="float32", always_2d=True)
            self.cache[path] = (data, rate)
        return self.cache[path]

    def load(self, runtime: Runtime, cue: Cue, seconds) -> None:
        path = cue.params.get("file_target", "")
        if path != "":
            try:
                self._load(path)
            except Exception:
                pass

    def start(self, runtime: Runtime, state: CueState) -> None:
        cue = state.cue
        if state.plan is None:
            return
        data, rate = self._load(cue.params["file_target"])
        voice = Voice(state, data, rate, state.plan, self.output_channels)
        self.voices[cue.unique_id] = voice

    def stop(self, runtime: Runtime, state: CueState, hard: bool) -> None:
        voice = self.voices.get(state.cue.unique_id)
        if voice is None:
            return
        natural = state.action_duration != INFINITE and state.action_elapsed >= state.action_duration - 1e-6
        if hard == False and natural == True:
            voice.ending = True
        else:
            del self.voices[state.cue.unique_id]

    def panic(self, runtime: Runtime, state: CueState, duration: float) -> None:
        pass

    # --- parametri ---
    def _crosspoints(self, cue: Cue, file_channels: int, patch_first: int) -> np.ndarray:
        levels = self.runtime.get_param(cue, "levels", {})
        main = levels.get("main", 0.0)
        trim = float(self.runtime.get_param(cue, "trim", 0.0))
        matrix = np.zeros((file_channels, self.output_channels), dtype=np.float32)
        explicit = [key for key in levels if "/" in key]
        if len(explicit) == 0:
            for channel in range(file_channels):
                target = patch_first + channel
                if 0 <= target < self.output_channels:
                    matrix[channel, target] = db_to_gain(0.0)
        else:
            for key in explicit:
                input_index, output_index = key.split("/")
                column = int(output_index) - 1
                row = int(input_index) - 1
                if 0 <= row < file_channels and 0 <= column < self.output_channels:
                    matrix[row, column] = db_to_gain(float(levels[key]))
        return matrix * np.float32(db_to_gain(float(main) + trim))

    def _patch_first(self, cue: Cue) -> int:
        patches = self.runtime.workspace.patches["audio"]
        number = int(cue.params.get("audio_output_patch", 1))
        if 1 <= number <= len(patches):
            return int(patches[number - 1].get("first_channel", 1)) - 1
        return 0

    # --- rendering ---
    def render(self, frames: int) -> np.ndarray:
        output = np.zeros((frames, self.output_channels), dtype=np.float32)
        solo = any(self.runtime.get_param(voice.state.cue, "solo", False) for voice in self.voices.values())
        for identifier in list(self.voices.keys()):
            voice = self.voices[identifier]
            state = voice.state
            if state.paused == True:
                continue
            cue = state.cue
            mute = self.runtime.get_param(cue, "mute", False) == True or (solo and not self.runtime.get_param(cue, "solo", False))
            block = self._render_voice(voice, frames)
            if block is None:
                del self.voices[identifier]
                continue
            if mute == False:
                output += block
        self._apply_output_mute_solo(output)
        low = db_to_gain(float(self.runtime.workspace.settings.get("min_volume", -60.0)))
        high = db_to_gain(float(self.runtime.workspace.settings.get("max_volume", 12.0)))
        return np.clip(output, -high * 4.0, high * 4.0).astype(np.float32)

    def _apply_output_mute_solo(self, output: np.ndarray) -> None:
        """Mute/solo delle uscite del dispositivo (numeri da 1) impostati nelle patch audio."""
        muted = set()
        soloed = set()
        for entry in self.runtime.workspace.patches["audio"]:
            muted.update(int(value) for value in entry.get("mute", []))
            soloed.update(int(value) for value in entry.get("solo", []))
        for channel in range(output.shape[1]):
            number = channel + 1
            if number in muted or (len(soloed) > 0 and number not in soloed):
                output[:, channel] = 0.0

    def _render_voice(self, voice: Voice, frames: int):
        cue = voice.state.cue
        times = voice.time + np.arange(frames) / self.sample_rate
        positions, valid = voice.plan.media_positions(times)
        if not valid.any() and voice.time > 0:
            return None
        voice.time = voice.time + frames / self.sample_rate
        source_index = positions * voice.file_rate
        left = np.clip(np.floor(source_index).astype(np.int64), 0, len(voice.data) - 1)
        right = np.clip(left + 1, 0, len(voice.data) - 1)
        fraction = (source_index - np.floor(source_index)).astype(np.float32)[:, None]
        samples = voice.data[left] * (1.0 - fraction) + voice.data[right] * fraction
        samples = samples * valid[:, None]
        matrix = self._crosspoints(cue, samples.shape[1], self._patch_first(cue))
        envelope = 1.0
        integrated = self.runtime.get_param(cue, "integrated_fade", {"enabled": False, "points": []})
        if integrated.get("enabled", False) == True and len(integrated.get("points", [])) > 0:
            gains = np.array([db_to_gain(envelope_value(integrated["points"], value)) for value in times],
                             dtype=np.float32)[:, None]
        else:
            gains = np.ones((frames, 1), dtype=np.float32)
        factor = self.runtime.gain_for(cue)
        if voice.state.panicking == True:
            duration = float(self.runtime.workspace.settings.get("panic_duration", 2.0))
            factor = factor * max(0.0, 1.0 - voice.state.panic_elapsed / max(duration, 1e-6))
        previous = voice.matrix_previous if voice.matrix_previous is not None else matrix
        ramp = np.linspace(0.0, 1.0, frames, dtype=np.float32)[:, None, None]
        # matrice interpolata nel blocco: niente "zipper noise" nei fade di livello
        matrix_curve = previous[None, :, :] * (1.0 - ramp) + matrix[None, :, :] * ramp
        mixed = np.einsum("fi,fio->fo", samples, matrix_curve) * gains * np.float32(factor)
        voice.matrix_previous = matrix
        mixed = self._apply_effects(voice, cue, mixed)
        return mixed.astype(np.float32)

    def _apply_effects(self, voice: Voice, cue: Cue, block: np.ndarray) -> np.ndarray:
        effects = self.runtime.get_param(cue, "audio_fx", [])
        if len(effects) == 0:
            return block
        from scipy.signal import lfilter
        result = block
        for index, effect in enumerate(effects):
            if effect.get("enabled", True) == False:
                continue
            kind = effect.get("type", "")
            if kind in ("peak", "lowshelf", "highshelf", "lowpass", "highpass"):
                b, a = biquad_coefficients(kind, float(effect.get("frequency", 1000.0)),
                                           float(effect.get("gain", 0.0)), float(effect.get("q", 0.707)),
                                           self.sample_rate)
                key = (index, kind)
                zi = voice.filter_state.get(key)
                if zi is None:
                    zi = np.zeros((max(len(a), len(b)) - 1, result.shape[1]))
                result, zi = lfilter(b, a, result, axis=0, zi=zi)
                voice.filter_state[key] = zi
            elif kind == "delay":
                delay_samples = max(1, int(float(effect.get("time", 0.25)) * self.sample_rate))
                feedback = float(effect.get("feedback", 0.3))
                mix = float(effect.get("mix", 0.5))
                buffer = voice.delay_buffers.get(index)
                if buffer is None:
                    buffer = np.zeros((delay_samples, result.shape[1]), dtype=np.float32)
                combined = np.concatenate([buffer, np.zeros_like(result)], axis=0)
                output = np.zeros_like(result)
                for frame in range(len(result)):
                    delayed = combined[frame]
                    output[frame] = result[frame] + mix * delayed
                    combined[frame + delay_samples] = result[frame] + feedback * delayed
                voice.delay_buffers[index] = combined[len(result):len(result) + delay_samples]
                result = output
        return result.astype(np.float32)

    # --- backend reale ---
    def open_stream(self, device=None):
        import sounddevice
        def callback(outdata, frames, time_info, status):
            with self.runtime.lock:
                outdata[:] = self.render(frames)
        self.stream = sounddevice.OutputStream(samplerate=self.sample_rate, channels=self.output_channels,
                                               blocksize=self.block_size, device=device, callback=callback)
        self.stream.start()
        return self.stream

    def close_stream(self) -> None:
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None


def render_offline(runtime: Runtime, mixer: AudioMixer, seconds: float, block: int | None = None) -> np.ndarray:
    """Avanza motore e mixer insieme e restituisce l'audio renderizzato (per test e export)."""
    block = block if block is not None else mixer.block_size
    chunks = []
    total = int(round(seconds * mixer.sample_rate))
    done = 0
    while done < total:
        count = min(block, total - done)
        chunks.append(mixer.render(count))
        runtime.advance(count / mixer.sample_rate)
        done = done + count
    return np.concatenate(chunks, axis=0) if chunks else np.zeros((0, mixer.output_channels), dtype=np.float32)
