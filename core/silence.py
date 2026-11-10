"""Step 1: silence removal, "Trim the start and end" or "Remove all silent parts".

The Slicer is ported verbatim from inspo/prototypes/1 .../audio_silence_remover.py (itself from
slicer2.py). It is pure numpy and cuts at RMS minima, which joins more smoothly than FFmpeg's
silenceremove. Only the loader changed: FFmpeg decodes to raw float32 PCM instead of
librosa.load(), which drops librosa, scipy and numba (~150 MB).
"""

from pathlib import Path

import numpy as np
import soundfile as sf

from core.measure import ProbeInfo, run_checked
from core.normalize import TARGET_RMS_PEAK_DB
from utils.ffmpeg import FFmpegRunner

# From the working prototype (docs/processing_spec.md), no GUI exposure, except:
# - the threshold follows the file's level, see silence_threshold()
# - min_length 300 instead of 3000: the Slicer returns any file shorter than min_length
#   untouched, which was nearly every sound effect, and only cut a middle pause once 3 s had
#   passed since the last cut. Pauses up to max_sil_kept (0.5 s) are still kept whole.
THRESHOLD_DB = -40.0
MIN_LENGTH_MS = 300
MIN_INTERVAL_MS = 300
HOP_SIZE_MS = 20
MAX_SIL_KEPT_MS = 500
EDGE_KEPT_MS = 100   # "Trim the start and end": quiet lead-in / tail kept, so onsets and fades survive

# Memory, for long files (an hour of stereo is 1.3 GB as float32): the decode goes to a temp
# file that is memory-mapped, and these bound the float64 RMS work and each write
RMS_BLOCK_HOPS = 1024        # ~7 MB of float64 at 20 ms hops
WRITE_BLOCK_SAMPLES = 1 << 20


def get_rms(y, *, frame_length=2048, hop_length=512, pad_mode="constant"):
    """Framewise RMS, same frames and values as slicer2.py's get_rms().

    The original built a strided (frame_length x frames) view and squared all of it, i.e. 4x
    the file's samples as a temporary: 2.7 GB for an hour of 48 kHz audio. With the window a
    whole number of hops (always true here: the Slicer uses 4 hops), summing squares per hop
    and then over each window gives the same result in a fraction of the memory. The zero
    padding is added a block at a time too, rather than to a padded copy of the whole file."""
    pad = int(frame_length // 2)
    n_frames = 1 + (y.shape[-1] + 2 * pad - frame_length) // hop_length
    if frame_length % hop_length or n_frames < 1 or pad_mode != "constant":
        return _get_rms_strided(np.pad(y, (pad, pad), mode=pad_mode), frame_length, hop_length)
    hops_per_frame = frame_length // hop_length
    n_hops = n_frames + hops_per_frame - 1
    hop_energy = np.empty(n_hops)
    end, step = n_hops * hop_length, RMS_BLOCK_HOPS * hop_length
    for s in range(0, end, step):   # s, e: positions in the padded signal
        e = min(s + step, end)
        block = np.zeros(e - s)     # float64
        lo, hi = max(s - pad, 0), min(e - pad, y.shape[-1])
        if hi > lo:
            block[lo + pad - s:hi + pad - s] = y[lo:hi]
        block = block.reshape(-1, hop_length)
        hop_energy[s // hop_length:e // hop_length] = np.einsum("ij,ij->i", block, block)
    window_energy = np.convolve(hop_energy, np.ones(hops_per_frame), mode="valid")
    power = np.maximum(window_energy, 0.0) / frame_length
    return np.sqrt(power)[np.newaxis, :]


def _get_rms_strided(y, frame_length, hop_length):
    """slicer2.py's original framing, for the case the fast path can't handle (y is padded)."""
    axis = -1
    out_strides = y.strides + tuple([y.strides[axis]])
    x_shape_trimmed = list(y.shape)
    x_shape_trimmed[axis] -= frame_length - 1
    out_shape = tuple(x_shape_trimmed) + tuple([frame_length])
    xw = np.lib.stride_tricks.as_strided(y, shape=out_shape, strides=out_strides)
    xw = np.moveaxis(xw, -1, axis - 1)
    slices = [slice(None)] * xw.ndim
    slices[axis] = slice(0, None, hop_length)
    x = xw[tuple(slices)]
    power = np.mean(np.abs(x) ** 2, axis=-2, keepdims=True)
    return np.sqrt(power)


class Slicer:
    def __init__(self, sr: int, threshold: float = -40., min_length: int = 5000,
                 min_interval: int = 300, hop_size: int = 20, max_sil_kept: int = 500):
        if not min_length >= min_interval >= hop_size:
            raise ValueError('The following condition must be satisfied: min_length >= min_interval >= hop_size')
        if not max_sil_kept >= hop_size:
            raise ValueError('The following condition must be satisfied: max_sil_kept >= hop_size')

        min_interval = sr * min_interval / 1000
        self.threshold = 10 ** (threshold / 20.)
        self.hop_size = round(sr * hop_size / 1000)
        self.win_size = min(round(min_interval), 4 * self.hop_size)
        self.min_length = round(sr * min_length / 1000 / self.hop_size)
        self.min_interval = round(min_interval / self.hop_size)
        self.max_sil_kept = round(sr * max_sil_kept / 1000 / self.hop_size)

    def _apply_slice(self, waveform, begin, end):
        if len(waveform.shape) > 1:
            return waveform[:, begin * self.hop_size: min(waveform.shape[1], end * self.hop_size)]
        else:
            return waveform[begin * self.hop_size: min(waveform.shape[0], end * self.hop_size)]

    def slice(self, waveform):
        if len(waveform.shape) > 1:
            samples = waveform.mean(axis=0)
        else:
            samples = waveform

        if (samples.shape[0] + self.hop_size - 1) // self.hop_size <= self.min_length:
            return [waveform]

        rms_list = get_rms(y=samples, frame_length=self.win_size, hop_length=self.hop_size).squeeze(0)
        sil_tags = []
        silence_start = None
        clip_start = 0

        for i, rms in enumerate(rms_list):
            if rms < self.threshold:
                if silence_start is None:
                    silence_start = i
                continue

            if silence_start is None:
                continue

            is_leading_silence = silence_start == 0 and i > self.max_sil_kept
            need_slice_middle = i - silence_start >= self.min_interval and i - clip_start >= self.min_length

            if not is_leading_silence and not need_slice_middle:
                silence_start = None
                continue

            if i - silence_start <= self.max_sil_kept:
                pos = rms_list[silence_start: i + 1].argmin() + silence_start
                if silence_start == 0:
                    sil_tags.append((0, pos))
                else:
                    sil_tags.append((pos, pos))
                clip_start = pos
            elif i - silence_start <= self.max_sil_kept * 2:
                pos = rms_list[i - self.max_sil_kept: silence_start + self.max_sil_kept + 1].argmin()
                pos += i - self.max_sil_kept
                pos_l = rms_list[silence_start: silence_start + self.max_sil_kept + 1].argmin() + silence_start
                pos_r = rms_list[i - self.max_sil_kept: i + 1].argmin() + i - self.max_sil_kept
                if silence_start == 0:
                    sil_tags.append((0, pos_r))
                    clip_start = pos_r
                else:
                    sil_tags.append((min(pos_l, pos), max(pos_r, pos)))
                    clip_start = max(pos_r, pos)
            else:
                pos_l = rms_list[silence_start: silence_start + self.max_sil_kept + 1].argmin() + silence_start
                pos_r = rms_list[i - self.max_sil_kept: i + 1].argmin() + i - self.max_sil_kept
                if silence_start == 0:
                    sil_tags.append((0, pos_r))
                else:
                    sil_tags.append((pos_l, pos_r))
                clip_start = pos_r
            silence_start = None

        # Handle trailing silence
        total_frames = rms_list.shape[0]
        if silence_start is not None and total_frames - silence_start >= self.min_interval:
            silence_end = min(total_frames, silence_start + self.max_sil_kept)
            pos = rms_list[silence_start: silence_end + 1].argmin() + silence_start
            sil_tags.append((pos, total_frames + 1))

        # Apply slices
        if len(sil_tags) == 0:
            return [waveform]
        else:
            chunks = []
            if sil_tags[0][0] > 0:
                chunks.append(self._apply_slice(waveform, 0, sil_tags[0][0]))
            for i in range(len(sil_tags) - 1):
                chunks.append(self._apply_slice(waveform, sil_tags[i][1], sil_tags[i + 1][0]))
            if sil_tags[-1][1] < total_frames:
                chunks.append(self._apply_slice(waveform, sil_tags[-1][1], total_frames))
            return chunks


def load_pcm(path: Path, info: ProbeInfo, runner: FFmpegRunner, raw: Path | None = None) -> np.ndarray:
    """Decode to float32 at the file's own rate and channel count. Shaped like
    librosa.load(mono=False): (samples,) for mono, (channels, samples) otherwise.
    With `raw`, FFmpeg decodes into that file and the result is a read-only memory map of
    it: reading a pipe holds the whole decode twice (2.5 GB for an hour of stereo). The
    caller deletes `raw` once every array taken from the result is gone."""
    channels = max(info.channels, 1)
    args = ["ffmpeg", "-hide_banner", "-nostats", "-y", "-i", str(path), "-map", "0:a:0",
            "-f", "f32le", "-acodec", "pcm_f32le", "-ac", str(channels), "-ar", str(info.sample_rate)]
    if raw is None:
        proc = run_checked(runner, [*args, "-"], "Reading the audio", binary_stdout=True)
        data = np.frombuffer(proc.stdout, dtype=np.float32)
    else:
        run_checked(runner, [*args, str(raw)], "Reading the audio")
        size = raw.stat().st_size // 4
        data = np.memmap(raw, dtype=np.float32, mode="r", shape=(size,)) if size else np.zeros(0, np.float32)
    data = data[:len(data) - len(data) % channels]
    return data if channels == 1 else data.reshape(-1, channels).T


def silence_threshold(rms_peak: float | None) -> float:
    """-40 dB below where the level matching will put the file, never above -40 dBFS.

    Silence removal runs before the level matching, so with a fixed -40 dBFS a very quiet
    recording's soft passages counted as silence: a -29 LUFS music file lost a minute of
    music. Judged relative to the file's own RMS peak, they survive. Loud files keep the
    prototype's -40, so nothing is ever trimmed harder than it used to be."""
    if rms_peak is None:
        return THRESHOLD_DB
    return min(THRESHOLD_DB, THRESHOLD_DB + rms_peak - TARGET_RMS_PEAK_DB)


def trim_ends(audio: np.ndarray, sr: int, threshold_db: float) -> np.ndarray:
    """Cut the silence before the first and after the last sound, keeping EDGE_KEPT_MS of
    each. Uses the Slicer's RMS measure, hop and window, so "silence" means the same thing in
    both modes. An all-silent file comes back unchanged."""
    samples = audio.mean(axis=0) if audio.ndim > 1 else audio
    hop = round(sr * HOP_SIZE_MS / 1000)
    win = min(round(sr * MIN_INTERVAL_MS / 1000), 4 * hop)
    rms = get_rms(y=samples, frame_length=win, hop_length=hop).squeeze(0)
    loud = np.flatnonzero(rms >= 10 ** (threshold_db / 20))
    if not loud.size:
        return audio
    keep = round(EDGE_KEPT_MS / HOP_SIZE_MS)
    start = max(0, (loud[0] - keep) * hop)
    end = min(samples.shape[0], (loud[-1] + 1 + keep) * hop)
    return audio[..., start:end]


def remove_silence(source: Path, dest: Path, info: ProbeInfo, runner: FFmpegRunner,
                   rms_peak: float | None = None, ends_only: bool = False) -> tuple[float, float]:
    """Write `source` minus its silent parts to `dest` as a 32-bit float WAV (lossless, and
    float keeps any overs a later effect adds until the gain stage pulls them down).
    rms_peak is the scan's measurement of `source`, for silence_threshold(). ends_only:
    only the start and end are trimmed (trim_ends()), pauses inside are left alone.
    Returns (seconds before, seconds after). If the Slicer leaves nothing (an all-silent
    file), the file is written unchanged, so the output folder stays complete."""
    if not info.sample_rate:
        raise ValueError("Unknown sample rate")
    raw = dest.with_suffix(".f32")
    try:
        return _remove_silence(source, raw, dest, info, runner, rms_peak, ends_only)
    finally:
        try:
            raw.unlink(missing_ok=True)
        except OSError:   # still mapped by a failing call's traceback; the batch's temp dir goes later
            pass


def _remove_silence(source, raw, dest, info, runner, rms_peak, ends_only):
    audio = load_pcm(source, info, runner, raw)
    if ends_only:
        chunks = [trim_ends(audio, info.sample_rate, silence_threshold(rms_peak))]
    else:
        slicer = Slicer(sr=info.sample_rate, threshold=silence_threshold(rms_peak), min_length=MIN_LENGTH_MS,
                        min_interval=MIN_INTERVAL_MS, hop_size=HOP_SIZE_MS, max_sil_kept=MAX_SIL_KEPT_MS)
        chunks = [c for c in slicer.slice(audio) if c.shape[-1]] or [audio]
    channels = 1 if audio.ndim == 1 else audio.shape[0]
    # Written a block at a time: joining the chunks first would be another copy of the file
    with sf.SoundFile(str(dest), "w", info.sample_rate, channels, subtype="FLOAT", format="WAV") as f:
        for chunk in chunks:
            for s in range(0, chunk.shape[-1], WRITE_BLOCK_SAMPLES):
                f.write(np.ascontiguousarray(chunk[..., s:s + WRITE_BLOCK_SAMPLES].T))
    kept = sum(c.shape[-1] for c in chunks)
    return audio.shape[-1] / info.sample_rate, kept / info.sample_rate
