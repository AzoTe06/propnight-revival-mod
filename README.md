# Propnight Revival mod and tools

Game-side part of [Propnight Revival](https://propnightrevival.online): a fan
project that keeps Propnight playable online after the end of the official
servers. Not affiliated with the game's developers or publisher. **No game file
is included**: the game comes from your own Steam library, and players install
everything with the [launcher](https://github.com/AzoTe06/propnight-revival-launcher).

## Mods (UE4SS 3.0.1, Lua)

- `mods/PropnightLocalMap`: hosting and joining (LAN and online through the
  revival relay), lobby fixes for listen-server hosts (role swap, host skins,
  player row, start button), first-person killer animations, restored maps
  support, in-game reports, `joinrelay` for the launcher's friends. Online mode
  is on when `online.txt` is next to it.
- `mods/PropnightLoginBypasser`: skips the dead login screen (from the
  Propnight Revived project, MIT, see its LICENSE).

Install: copy both folders to `Propnight/Binaries/Win64/Mods/` of a game with
UE4SS 3.0.1, and enable them in `Mods/mods.txt`.

## Tools

- `tools/kismet/`: reading and editing cooked Blueprints through UAssetGUI JSON
  (`bp.py` statements, `trace.py` execution flow of an event, `offsets.py`),
  building the revival paks (`build_modpak.py`), localisation, map props.
- `tools/online/build_online_pak.py`: the small pak that points the game at the
  revival backend.

These tools need [UAssetGUI](https://github.com/atenfyr/UAssetGUI) and
[repak](https://github.com/trumank/repak), and work on files extracted from
your own copy of the game.

## Notes

`docs/OPEN_SOURCE.md` lists what is published and what never is.

## License

MIT, see [LICENSE](LICENSE).
