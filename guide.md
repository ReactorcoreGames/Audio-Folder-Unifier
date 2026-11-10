# Audio Folder Unifier — Guide

## TL;DR

1. Install FFmpeg if you don't have it: https://reactorcore.itch.io/ffmpeg-to-path-installer
2. Run `Audio Folder Unifier.exe`, click **Browse** next to "From" and pick your folder.
3. Pick what kind of audio it is (Sound Effects, Voice & Speech, Music Tracks or Ambient Loops).
4. Optionally pick an effect from "Change the sound?".
5. Press **Start**. The results go into a `unified` folder inside your folder. Your originals are never changed.

---

## 1. Choose your folders

- **From:** the folder with your audio. As soon as you pick it, the program counts the audio files and checks their loudness. The line under the progress bar shows what it found, for example "Found 47 audio files · 6 look unusually quiet".
- **To:** where the results go. It fills in `<your folder>\unified` for you; click its **Browse** to pick somewhere else.
- **Include subfolders:** also processes the audio in every folder inside the From folder. The output gets the same folder tree.

The program never processes its own output, even when the To folder is inside the From folder, so running it twice is safe.

## 2. What kind of audio is this?

This is the only choice you have to make. It decides *how* loudness is measured and how loud everything ends up. It never changes the sound itself, so a wrong pick is harmless: the files just come out a bit too quiet or too loud, and you run it again.

| Pick | For | Ends up at |
|---|---|---|
| **Sound Effects** | game sounds, foley, blips, UI clicks | -13 dBFS RMS peak |
| **Voice & Speech** | narration, podcasts, ASMR, audiobooks | -16 LUFS |
| **Music Tracks** | songs, loops, stingers | -14 LUFS |
| **Ambient Loops** | rain, forest, machinery, room tone | -20 LUFS (quieter, so it sits under other sounds) |

Files shorter than 3 seconds always use the Sound Effects method, whatever you pick. The usual loudness measurement can't judge such short sounds and would blow them up into distortion. The log says when this happens.

Nothing ever clips: the program keeps every file's peaks under the ceiling, even if that means a very spiky file ends up a little under the target.

## 3. Change the sound? (optional)

The default, **No change — just fix the loudness**, leaves the sound alone. Everything else gives *every* file in the folder the same character. The box under the dropdown describes the selected effect.

Effects are applied first and the loudness is matched afterwards, so even heavy effects keep the folder consistent. That's also why **Gritty** and **Brutal** won't sound louder than the rest: distortion makes a sound seem louder, so the program turns it down to match.

### Match everything to one quality level

NES, SNES, PlayStation 1, Nintendo 64, Sega Saturn, PlayStation 2. This is the strongest way to make mismatched sounds feel like one set. Sounds gathered from different places don't only differ in loudness; they differ in *texture*: one is a crisp studio recording, another a crunchy old clip. Pushing them all through the same lower quality gives them a shared texture, and then they belong together.

The list is a **ladder ordered by strength, harshest first**. The console names are a quick way to say how hard the effect hits ("NES" is obviously rougher than "PlayStation 2"), with a bit of each console's flavour on top. They are not exact recreations of those consoles' sound chips.

- **NES:** the harshest. Thin, buzzy and crunchy.
- **SNES:** muffled and crunchy, with a faint echo.
- **PlayStation 1:** clearly lo-fi, grainy, with roomy reverb. A good middle setting.
- **Nintendo 64:** dull and cavernous with a big echo. Good for harsh or hissy sources.
- **Sega Saturn:** dreamy, with long floating echoes. The mood setting.
- **PlayStation 2:** the lightest. Bright and gritty. Good for dull sources.

#### Important: the quality level only pulls down, never up

The quality ladder can only make better-sounding files worse. It can't make a bad file better. If one of your files is already a muffled, crunchy old recording and you pick PlayStation 2, that file stays muffled and crunchy, while everything else only gets a little grit, so it will still stick out.

**Pick a rung at or below your worst file.** Listen to the roughest file in your folder and pick the setting that sounds at least that rough. If unsure, try PlayStation 1 first and move up or down the ladder.

### Sounds like it's coming from

A radio, a telephone, a megaphone / PA, underwater, an old cassette tape, an old vinyl record, far away in another room, Gritty (mild distortion) and Brutal (heavy distortion). Strong effects, good for making a set of voice lines or sounds share one "place".

### Polish & finish

Gentler, corrective effects: **Podcast polish** (clearer, more even speech), **Punchy sound effects** (harder-hitting impacts), **Warm & fuzzy**, **Bright & crisp** (for dull or muffled recordings).

## 4. Extras (optional)

- **Silence:**
  - *Keep it* (default): nothing is cut.
  - *Trim the start and end:* cuts the silence before the first sound and after the last one. Pauses in the middle stay.
  - *Remove all silent parts:* also shortens long pauses in the middle. Short natural pauses (up to about half a second) are kept.
- **Only fix the files that are unusually quiet:** processes only the files that are much quieter than the rest of the folder (10 dB or more under the folder's typical level). It becomes clickable once the scan has found some; it needs at least 5 files to compare.
- **Save as:** *Same as original*, WAV, MP3 or OGG.

## Start, Stop and the results

- **Start** processes the folder. The progress bar, the current file and the log show how it goes.
- **Stop** stops right away. The file that was in progress is not left half-written.
- **Open output folder** (bottom left) opens the To folder.

Output files get a suffix that says what was done, for example:

```
explosion.wav  + Sound Effects                      → explosion_sfx.wav
narration.mp3  + Voice & Speech, trim start and end → narration_voice_t.mp3
song.flac      + Music Tracks, PS1, remove silence  → song_music_ps1_x.flac
```

Running again with the same settings overwrites those files; different settings write new files alongside them, so you can compare.

If a file can't be read (damaged or not really audio), it's listed as failed in the log and the rest go on. If the folders themselves become the problem (the From folder is deleted, the To folder can't be written to, the disk is full), the program stops and tells you why.

## Files next to the exe

- `config.json` remembers your last folders and choices.
- `log.txt` keeps the log of every run, since the box in the window is small. You can delete it whenever it gets big; a new one is made.

Don't keep your real work inside the program's own folder if you ever replace it with a newer version.

## Troubleshooting

- **"FFmpeg not found":** install it with https://reactorcore.itch.io/ffmpeg-to-path-installer, then restart the program.
- **"Windows doesn't allow saving files there":** pick a To folder you can write to, such as one in your Documents.
- **"There are no audio files in..."**: if your audio is in folders inside the one you picked, tick "Include subfolders".
- **A file came out quieter than expected:** very spiky material (sharp hits, loud peaks) can't be raised all the way without clipping, so it stops a little under the target. That's on purpose.
- **Speech or music under 3 seconds sounds louder than the rest:** see the 3-second rule in section 2.

The exact numbers behind every preset are in `stats-for-nerds.md`.

---

## Contact

mailto:reactorcoregames@gmail.com

---

Check out everything else I do: ✨🚀

https://reactorcoregames.github.io/

https://reactorcore.itch.io/

-Reactorcore

---

My other links:
Home/Links: https://reactorcoregames.github.io/
Releases: https://reactorcore.itch.io
Blog: https://www.patreon.com/ReactorcoreGames
Discord: https://discord.gg/UdRavGhj47
Backup links page: https://linktr.ee/reactorcore
