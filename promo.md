# Audio Folder Unifier — Promo notes (internal, not shipped in the release zip)

## Strategy

### What this is, in one line

A standalone Windows tool that makes a whole folder of audio consistent: same loudness for every file (with a method that works on short game sounds), plus optional effects that give every file the same character, from a retro console "quality ladder" to radio, cassette tape and vinyl.

### Who it's for

- Indie and hobby game devs with a sound folder gathered from ten different free packs, where every file is a different volume and a different texture.
- Game jam teams who need their grabbed-from-everywhere sounds to feel like one game in an afternoon.
- Podcasters, narrators and audiobook makers levelling a folder of takes or episodes.
- Modders and retro-style devs who want their sounds to fit a PS1 or SNES look.
- Anyone with a messy sound library who doesn't know (or want to know) what LUFS means.

### Why it gets found

The pitch is a pain everyone with a sound folder already has: "why is this one so loud?". Lead with that, then the hook nobody else has: the console quality ladder that turns mismatched sounds into one set. A short before/after audio clip (the same 6 random sounds, raw vs. through PS1) sells it faster than any text; make one for the itch page and the video.

### Tactics

- **Post in persistent, searchable places first** (itch.io page, GitHub repo, AlternativeTo, KVR, curated gamedev tool lists). They keep sending traffic for years with no upkeep.
- **Name the problem in the words people search for:** "normalize audio folder", "batch normalize sound effects", "make sound effects same volume", "lo-fi / PS1 sound effect filter", "retro audio effect". Searchers don't type "unifier".
- **Before/after audio on the itch page.** itch supports embedded SoundCloud/YouTube. A 30 s clip: six sounds raw, then the same six through Sound Effects + PS1.
- **Show the ladder.** One devlog or social post per rung (NES, SNES, PS1, N64, Saturn, PS2) with a short clip of the same sound through each is six ready-made posts for itch devlogs, Bluesky/Mastodon/X `#gamedev` `#indiedev` `#gameaudio`, and the Discord.
- **Cross-link from your other audio programs** (Easy Audio ASMRifier, Audio Satanifier, the Script-to-Voice generators, the FFmpeg installer). Their users are the same people, and the FFmpeg installer page is already a natural "you'll also want this" spot.
- **Give away an example pack:** a free CC0 set of sounds run through the ladder on OpenGameArt/itch, with "made with Audio Folder Unifier" and a link. Asset browsers become tool users.

### Business model: honest estimate

- **Market reality:** "batch normalize audio" is a long-solved problem for engineers (Audacity macros, ffmpeg scripts, paid mastering tools), so the general case won't sell on its own. What's distinct here is the no-jargon, can't-go-wrong framing, the short-SFX method that loudness tools get wrong, and the quality ladder. Those win attention from laypeople and gamedevs, the audience least willing to script ffmpeg.
- **The fit:** the source is MIT on GitHub. That suits a tool like this: it's eligible for "awesome" lists and GitHub topic pages, the best long-term traffic sources, and it doubles as portfolio work. On itch, the ready-made Windows build can be free, pay-what-you-want, or paid; under MIT very few laypeople will build the exe themselves, so a paid or PWYW build stays viable, with a "buy the ready build to support development" line in the README.
- **Traffic value:** whichever price you pick, the tool's best use may be as a funnel: every user is a gamedev or creator who'd like your other tools, and the in-app footer and the release's homepage link point them there.
- Pricing is your call. These are directions only.

### Marketing targets (persistent places)

1. **itch.io tools section:** publish as Kind "Tool", classification "Tools", with the tags below. Devs browse `itch.io/tools/tag-audio` and `tag-sound-effects` when shopping for exactly this.
2. **ellisonleao/magictools** (GitHub), the best-known gamedev tools list, has an Audio section: https://github.com/ellisonleao/magictools — open a PR adding it there. Similar: https://github.com/mbrukman/awesome-game-dev
3. **KVR Audio product database**: https://www.kvraudio.com/ — the long-running catalogue of audio software; developers can list standalone apps as well as plugins, and its pages rank well in search.
4. **AlternativeTo**: https://alternativeto.net/ — list it as an alternative to audio normalizers and batch processors (e.g. MP3Gain, Audacity's macro normalising). Low effort, indexed, permanent.
5. **OpenGameArt.org**: post the free CC0 sample pack (sounds through the ladder) with a link in the description. Its audience is the target user.

---

## itch.io

### Name of project

Audio Folder Unifier

### Subtitle (100 characters max)

Make a whole folder of audio sound consistent: same loudness, plus 19 effects from NES crunch to vinyl

### Long description (markdown)

```markdown
# Audio Folder Unifier

**This is a Windows program that makes a whole folder of audio sound like it belongs together, in one click.**

You've collected sounds from everywhere: some are quiet, some blast your ears, some are crisp studio recordings and some are crunchy old clips. Point Audio Folder Unifier at the folder and it writes out a new one where every file sits at the same loudness. Your originals are never touched.

## The right method for every kind of audio

Pick what your audio is and the program does the rest:

- **Sound Effects:** game sounds, foley, blips, UI clicks. Uses a method that actually works on short sounds, which ordinary loudness tools get wrong (a 200 ms blip measures as near-silence and gets blown up into distortion).
- **Voice & Speech:** narration, podcasts, ASMR, audiobooks (-16 LUFS).
- **Music Tracks:** songs, loops, stingers (-14 LUFS, the streaming standard).
- **Ambient Loops:** rain, forest, machinery, room tone (-20 LUFS, so it sits under everything else).

Nothing ever clips, and you can't pick wrong: the worst case is a re-run.

## Make them belong together: the quality ladder

Sounds from different places don't just differ in volume; they differ in *texture*. Push them all through the same retro quality level and they finally feel like one set:

**NES → SNES → PlayStation 1 → Nintendo 64 → Sega Saturn → PlayStation 2**

From harsh 8-bit crunch to a light, bright grit, each with a bit of its console's flavour.

## Or make it sound like it's coming from...

A radio, a telephone, a megaphone, underwater, an old cassette tape, an old vinyl record, another room, or crank it with Gritty and Brutal distortion. Plus polish presets: podcast polish, punchy sound effects, warm & fuzzy, bright & crisp.

## Also

- Trim silence at the start and end, or remove all silent parts
- Finds the files that are unusually quiet and can fix only those
- Saves as the original format, WAV, MP3 or OGG
- Subfolders, hundreds of files at once, stop any time
- No jargon: every option says what it sounds like. The exact numbers are in the included "stats for nerds" document

## How to use

1. Install FFmpeg if you don't have it, with my one-click installer: https://reactorcore.itch.io/ffmpeg-to-path-installer
2. Unzip, run `Audio Folder Unifier.exe` (Windows, no install)
3. Pick your folder, pick what kind of audio it is, press Start
4. The results appear in a `unified` folder next to your sounds

A guide (`guide.md`) is included. Source code on GitHub under the MIT license.

---

Check out everything else I do: ✨🚀
https://reactorcoregames.github.io/

-Reactorcore
```

### Tags (10, comma separated)

audio, sound-effects, normalization, gamedev, batch, retro, lo-fi, game-audio, tool, windows

---

## GitHub

### Description blurb

Make a whole folder of audio sound consistent: loudness matching that works on short SFX, plus a retro quality ladder (NES to PS2) and 13 more effects. Python + ttkbootstrap + FFmpeg, Windows exe.

### Topics (10, one per line)

audio
audio-normalization
loudness
ffmpeg
batch-processing
game-audio
sound-effects
lofi
python
tkinter

---

## YouTube (showcase / trailer)

### Title

Audio Folder Unifier: Make Every Sound in a Folder Belong Together (Windows Tool)

Video: `trailer/trailer_16x9.mp4` (48 s, 1080p). No price is mentioned anywhere: the release page says it.

### Description

```
Audio Folder Unifier is a Windows program that makes a whole folder of audio sound consistent in one click. Every file comes out at the same loudness, using the right method for sound effects, voice, music or ambience, and it works on short game sounds, which ordinary loudness tools get wrong.

Want them to really belong together? Push every file through the same retro quality level, from NES crunch to PlayStation 2 grit, or make them all sound like a radio, a telephone, a cassette tape, vinyl, underwater, another room, or brutally distorted.

Pick a folder, pick what kind of audio it is, press Start. Your originals are never touched.

Get it: https://reactorcore.itch.io/audio-folder-unifier

In the video: five CC0 sound effects before and after (the after is the program's real output, nothing touched up by hand), then the voice line "Unify your audio." through the NES, PS1, Saturn and PS2 quality levels.
Music: "Sunday Drive" by Silent Partner (YouTube Audio Library)

Made by Reactorcore

Contact: reactorcoregames@gmail.com

Check out everything else I do: ✨🚀
Home/Links: https://reactorcoregames.github.io/
Releases: https://reactorcore.itch.io
Blog: https://www.patreon.com/ReactorcoreGames
Discord: https://discord.gg/UdRavGhj47
Backup links page: https://linktr.ee/reactorcore

-Reactorcore
```

### Tags (comma separated)

audio normalizer, batch normalize audio, sound effects, game audio, gamedev, indie dev, loudness, lufs, lo-fi audio, retro sound effects, ps1 sound, 8-bit sound, audio tool, ffmpeg, windows tool

### Shorts

Video: `trailer/trailer_shorts.mp4` (same cut, 9:16).

Title: `Make every sound in your folder match, in one click #gamedev #indiedev #gameaudio`

Description:

```
Audio Folder Unifier: one click brings a whole folder of audio to the same loudness, with optional retro effects from NES to PS2 to give every file the same texture. Windows.

Get it: https://reactorcore.itch.io/audio-folder-unifier
Music: "Sunday Drive" by Silent Partner (YouTube Audio Library)
```

---

## Discord post
(attach a screenshot + cover image with the post)

### Title
Audio Folder Unifier: make every sound in a folder belong together

### Post content
```
## Audio Folder Unifier
(make every sound in a folder belong together)

Release: https://reactorcore.itch.io/audio-folder-unifier

A Windows program that takes a folder of audio gathered from everywhere and makes it consistent in one click: every file at the same loudness (it works on short game sounds too), with optional effects to give them all the same character. Retro quality ladder from NES to PS2, radio, telephone, cassette tape, vinyl, underwater, brutal distortion and more.

Standalone, unlimited, no jargon, and your originals are never touched.
```
