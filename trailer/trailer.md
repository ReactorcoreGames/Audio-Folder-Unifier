# Audio Folder Unifier — YouTube trailer plan

Status: rendered 2026-11-09 (trailer_16x9.mp4, trailer_shorts.mp4).

## Music

`Sunday Drive - Silent Partner.mp3` (YouTube Audio Library, no attribution needed, can't be shipped on its own, so it stays out of the release zip and `trailer/` stays out of the build).

- 133.4 s long, about 86 BPM, so one beat is 0.697 s and one bar is 2.786 s. Bar downbeats sit at 2.18 s + n × 2.786 s (2.18, 4.97, 7.76, 10.54, 13.33, 16.12, 18.90, 21.69, 24.48, 27.26, 30.05, 32.84, 35.62, 38.41, 41.20, 43.98, 46.77 …).
- 0–11 s is a quiet intro (about -18 dB), the full band comes in at about 11.1 s, the body runs steady until about 100 s, then a soft outro and a fade.
- The track starts at 0 and fades out when the video ends (about 3 s fade), as usual.
- **One deliberate exception:** during the demo shots the music is ducked by about 14 dB (smooth 0.3 s ramps), otherwise it hides the very difference we're showing. It comes back to full level for the effects montage and the outro.

## Demo audio

- **Before / after set:** five CC0 sounds from `test/testfiles/sound effects`, picked for a wide spread in loudness and for being recognisable at a glance. Candidates: `glass-breaking-2` (loud), `sand-step` or `raven-2` (barely audible), `dinosaur-1` (quiet roar), `explosion-2` (loud), `gold-1` (quiet coin jingle). Each one is trimmed to ≤1.3 s. I make the final pick by measuring, so the set alternates loud and quiet.
- **Before** keeps the files' real level differences, but the whole set is lowered together so the loudest one doesn't jump out over the music and startle anyone. The gaps between files stay true.
- **After** is the real pipeline output: `test/run_folder.py` with category Sound effects and No change. Nothing is faked or hand-levelled.
- **Ladder voice:** a short TTS line, generated with the same Windows voice used in Session 5 (Microsoft David): *"Unify your audio."*, run through the real pipeline with category Voice and each rung's effect. Speech shows texture changes better than any sound effect.

## Look

The app's own palette (dark teal `#0B2226`, neon `#C8FF2E`, soft `#E4FF9C`, white `#F2FBF7`) and Segoe UI, as in `promo/`. Frames are built with PIL and assembled with FFmpeg. Waveforms are drawn from the actual audio on one shared scale, so they show the real level difference even with the sound off. Text moves in broad strokes on bar lines, not on every beat.

## Shot list (16:9, 1920×1080, about 48 s)

| # | Time (s) | Bars | Music | Picture | Audio on top |
|---|---|---|---|---|---|
| 1 | 0.00–4.97 | intro | full (quiet intro) | Icon fades in, then the title **Audio Folder Unifier** and the tagline *"Make a folder of sounds belong together."* | — |
| 2 | 4.97–13.33 | 3 | ducked | Header *"Sounds from everywhere…"*. Five file chips appear one at a time, each with its waveform drawn as it plays. Some are huge, some are slivers. Caption on the last bar: *"…every one a different volume."* | the 5 raw sounds |
| 3 | 13.33–16.12 | 1 | ducked | A screenshot of the real window (Sound effects category, PS1-style done state from the promo set or a new capture) with a slight push-in. Start highlights, the progress bar fills. Caption: *"Pick a folder. Press Start."* | soft UI click |
| 4 | 16.12–24.48 | 3 | ducked | The same five chips in the same order. Their waveforms now come out matched. Caption: *"Same loudness. No settings to learn."* A small badge underneath: *"Short sound effects done right, not boosted into clipping."* | the 5 unified sounds |
| 5 | 24.48–35.62 | 4 | ducked | **The quality ladder.** A six-step ladder graphic (NES → SNES → PS1 → N64 → Saturn → PS2, strongest first). One bar each for **NES, PS1, Saturn and PS2**: the rung lights up and the voice line plays through it. Caption: *"…or give them one shared texture."* | the voice line ×4 |
| 6 | 35.62–41.20 | 2 | back to full | Kinetic list of the other effects, in broad strokes: *Radio · Telephone · Megaphone · Underwater · Cassette · Vinyl · Another room · Gritty · Brutal · Podcast polish · Punchy · Warm · Bright*, ending on *"19 effects. Your originals are never touched."* | — |
| 7 | 41.20–48.0 | 2+ | full, fades from about 45 s | Icon, name, *"Windows · Open source"*, *"reactorcore.itch.io"*. The trailer never mentions price. Fade to black. | — |

Why only four rungs in shot 5: six bars of the same line would drag in a trailer this short. NES → PS1 → Saturn → PS2 still shows the strength range and the flavour differences. The ladder graphic shows all six names so none feel missing.

## Shorts version (9:16, 1080×1920, same cut and same audio)

Same timeline. The layout is stacked: the title/caption block on top, the waveform lane in the middle (chips listed vertically), and the window screenshot scaled to fit the width in shot 3. Captions get larger.

## Process

1. Pick and measure the five sounds, render before/after through the pipeline, and generate the voice line and its four rungs. Assets go in `trailer/work/` (gitignored if a repo appears).
2. Capture any new window shots with the existing promo scripts (config.json is backed up and restored).
3. Render a 480p draft of the 16:9 version for you to watch, then fix what you flag.
4. Final 1080p renders: `trailer/trailer_16x9.mp4` and `trailer/trailer_shorts.mp4`.
5. Add the YouTube title, description and tags to `promo.md`.

## Decisions

- No price in the trailer or YouTube text: the release page says it. The only link is reactorcore.itch.io.
- Voice line: "Unify your audio."
