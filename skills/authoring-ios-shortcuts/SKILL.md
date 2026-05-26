---
name: authoring-ios-shortcuts
description: Use when the user wants to create, generate, or modify an iOS/macOS Shortcut programmatically (i.e. without tap-tap-tapping in the iPhone Shortcuts editor). Triggers on "make a shortcut", "build an Apple Shortcut", "iPhone shortcut", "send X from voice memos / messages / etc.", "Shortcut that POSTs to my API", or any request to wire an iPhone behavior to a Cloudflare worker / webhook. Compiles a Cherri DSL source file to a signed `.shortcut`, opens it in macOS Shortcuts.app, then iCloud-syncs to the user's iPhone. Returns an iCloud share link that installs on any device with one tap.
---

# Authoring iOS Shortcuts (Cherri pipeline)

**Announce at start:** "Using authoring-ios-shortcuts to build [name]."

## Why this exists

Apple Shortcuts is a fantastic glue layer but the editor is tap-based and unauthorable. The community has reverse-engineered the `.shortcut` plist format into a typed DSL — **Cherri** — that compiles to a signed Shortcut. Once you have the DSL, every Shortcut you ever want to make is a code edit + one terminal command + one click on macOS to install. No more 30-minute editor sessions for a 9-action flow.

`shortcuts-js` (the JS equivalent) is **archived and unmaintained**. Do not use it.

## Prerequisites (verify before doing anything else)

```bash
# Required:
which cherri || brew tap electrikmilk/cherri && brew install cherri
which shortcuts                 # built into macOS, no install needed
sw_vers                         # macOS Sequoia (15) or later — signing is required on this version

# Sanity:
cherri --version
shortcuts --help                # confirm `sign` subcommand is present
```

**Signing is non-skippable on iOS 17+ / macOS Sequoia+.** The "Allow Untrusted Shortcuts" toggle has been removed. Every `.shortcut` file must be signed before macOS or iOS will import it. Cherri wraps `shortcuts sign` automatically when given `-s=anyone`.

## The 5-step build loop

```
1. Author       → shortcuts/<name>.cherri
2. Compile      → cherri shortcuts/<name>.cherri -s=anyone -o=shortcuts/build/<name>.shortcut
3. Install      → open shortcuts/build/<name>.shortcut
                  (user clicks "Add Shortcut" in the macOS sheet — one click)
4. iCloud sync  → ~30 seconds; appears on iPhone library automatically
5. Share link   → right-click tile in macOS Shortcuts.app → Share → Copy iCloud Link
                  (link installs on any iPhone with one tap; mode=anyone required)
```

After step 3, verify with `shortcuts list | head` — the new slug should appear at the top.

## Cherri syntax cheat sheet

### File header

```cherri
#define name My Shortcut
#define color red               // red, orange, yellow, green, blue, purple, pink, grey, etc.
#define glyph microphone        // search glyphs at https://glyphs.cherrilang.org/
#define mac false               // true = also runs on macOS; false = iOS-only

#include 'actions/<category>'   // see category list below — one per category used
```

### Variables

```cherri
@mutable = "value"              // → Set Variable action (heavier, mutable across the script)
const immutable = action(...)   // → magic-variable reference (lighter, recommended default)
const x = "interp {var} works"  // double-quoted strings interpolate {var} and {@var}
@y = 'no interp here {var}'     // single-quoted strings are LITERAL (no interpolation)
```

### Dictionaries

```cherri
@d = {
    "filename": "{filename}",    // text via interpolation
    "count": 5,                  // bare number → Number type
    "active": true,              // bare bool → Boolean type
    "nested": { "key": "v" },    // nested dict
    "arr": [1, 2, 3]
}
```

**Pitfall:** Cherri parses dict literals as **strict JSON** — `"key": variable` (bare identifier value) errors with `JSON error: invalid character...`. If you need a variable's NUMERIC type preserved in a dict literal, you cannot do it in Cherri. Either:
- Send as string + coerce on the server (`z.coerce.number()` in zod, etc.) — simplest
- Use `rawAction("is.workflow.actions.dictionary", { WFItems: ... })` with manual `WFItemType: 3` entries — full control, ugly

### Raw actions (escape hatch)

For any Shortcut action not in Cherri's stdlib, drop to raw:

```cherri
rawAction("is.workflow.actions.downloadurl", {
    "WFURL": "https://...",
    "WFHTTPMethod": "POST",
    "WFRequestVariable": "${@bodyVar}"     // ${@var} mutable, ${var} const
})
```

Reusable raw action — declare once, call like a stdlib function:

```cherri
// Single-line declaration ONLY — multi-line parses as a syntax error.
action 'is.workflow.actions.properties.files' getFileDetails(variable input: 'WFInput', text property: 'WFContentItemPropertyName')

const name = getFileDetails(memo, "Name")
```

The `is.workflow.actions.` prefix is auto-prepended when the identifier has ≤4 dotted parts.

## Include-by-category table

Cherri requires explicit `#include` for each category you touch. The error message names the missing one:

| `#include` directive          | Provides actions like                                            |
|-------------------------------|------------------------------------------------------------------|
| `'actions/basic'`             | `alert`, `show`, `prompt`, `confirm`, `showNotification`         |
| `'actions/media'`             | `searchVoiceMemos`, `recordAudio`, `playMusic`                   |
| `'actions/web'`               | `jsonRequest`, `formRequest`, `downloadURL`, `urlEncode`         |
| `'actions/scripting'`         | `getFirstItem`, dictionary helpers, conditionals                 |
| `'actions/documents'`         | `getFileDetail` (singular), `getFileFromFolder`                  |
| `'actions/calendar'`          | `formatDate`, `date`, `currentDate`                              |
| `'actions/crypto'`            | `base64Encode`, `base64Decode`, hash functions                   |
| `'actions/network'`           | `getExternalIP`, wifi/hotspot — **NOT** HTTP (that's `web`)      |
| `'actions/text'`              | `text`, `splitText`, `replaceText`, `lowercase`                  |
| `'actions/location'`          | `getCurrentLocation`, `getAddresses`                             |
| `'actions/images'`            | `getDetailsOfImages`, `convertImage`                             |

If unsure, run `cherri --action=<name>` to find which include defines a given action.

## Common pitfalls

1. **`#define mac false`** disables Mac execution, so testing on Mac always fails. Switch to `true` for cross-platform testing.
2. **No "Get Latest Voice Memo" action.** Use `searchVoiceMemos("")` (empty query returns ALL voice memos newest-first) then `getFirstItem(memos)`.
3. **`getFileDetail` is in stdlib already** — collides with custom `action` declarations of the same name. Rename custom raw actions (e.g., `audioDetail`, `fileDetailsPlural`).
4. **Multi-line `action` declarations** cause `Illegal character` errors. Keep on a single line.
5. **Block comments `/* ... */`** confuse the parser intermittently. Prefer `//` line comments.
6. **`\"` escape inside double-quoted strings** doesn't work. To embed `"` use single-quoted strings, but lose interpolation.
7. **`jsonRequest`'s `body` argument rejects variable refs** — requires an inline dict literal. For dynamic JSON bodies, build the dict via interpolated values (all-string), or use `rawAction("is.workflow.actions.downloadurl", { WFHTTPBodyType: "File", WFRequestVariable: "${var}" })`.
8. **Output files land in the source dir, not the cwd.** Use `-o=` explicitly to control destination.
9. **`shortcuts sign --mode anyone`** is required for shareable iCloud links. Default mode `contacts` greys out the Copy iCloud Link option.
10. **`base64Encode(memo)` on a voice memo encodes the asset URL, not the file bytes.** `searchVoiceMemos("")` + `getFirstItem` returns a `WFAVAsset`. When passed to `base64Encode` (whose `WFInput` expects text-or-file), Shortcuts coerces the asset to its file-URL/metadata text. The base64 string LOOKS valid (decodes fine via `atob`), but the bytes are ASCII URL text — any audio API receives garbage and returns "corrupt or unsupported data". **Fix:** force file materialization with `encodeAudio(memo, "M4A", "Normal")` (from `actions/media`) before base64Encode. The Encode Audio action outputs a real media file the next action treats as bytes. Cost: ~1-2s extra per memo. Verified May 2026 via direct curl test (worker accepts hand-crafted `say` + `afconvert` m4a fine → bug is 100% in Shortcut's asset→base64 coercion).

## Worktree-shareable iCloud link extraction

After `open file.shortcut`:

1. macOS Shortcuts.app pops an **"Add Shortcut"** sheet showing the action preview.
2. User clicks **Add Shortcut**. Tile lands in the library.
3. macOS auto-syncs to iCloud (~30s).
4. Right-click tile → **Share** → **Copy iCloud Link** → paste link wherever needed.

The CLI cannot generate iCloud links — Apple gates the signing service behind the GUI Share menu. There is **no `shortcuts share`** or `shortcuts export-link` subcommand.

## Recipe template

```cherri
// <description of what this Shortcut does>

#define name <Friendly Name>
#define color <color>
#define glyph <glyph>
#define mac false

#include 'actions/<category1>'
#include 'actions/<category2>'

// Optional reusable raw actions:
action 'is.workflow.actions.<id>' niceName(variable input: 'WFInput')

@authHeader = "Bearer <TOKEN>"  // factor secrets to top so rotation is one edit

// ... your action chain ...

const response = jsonRequest("https://...", "POST", {
    "key": "{var}"
}, {"Authorization": "{@authHeader}"})

showNotification("Done: {response}", "<Friendly Name>")
```

Build:
```bash
cherri shortcuts/<name>.cherri -s=anyone -o=shortcuts/build/<name>.shortcut
open shortcuts/build/<name>.shortcut    # macOS install sheet
```

## Reference

- Cherri language docs: https://cherrilang.org/language/
- Cherri repo (tests dir has real-world examples): https://github.com/electrikmilk/cherri/tree/main/tests
- Glyph search: https://glyphs.cherrilang.org/
- Worked example (voice memo → Worker): `shortcuts/send-to-second-brain.cherri` in `unleashed-memory` repo
