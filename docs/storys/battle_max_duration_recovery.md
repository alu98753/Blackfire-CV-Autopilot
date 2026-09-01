# Battle maximum-duration recovery

## Purpose

Prevent a frozen game screen that still matches battle UI templates from trapping the automation in `BATTLE` indefinitely.

## Action

Added the TOML-only `[global].battle_max_duration_sec` default (900 seconds). `BattleHandler` checks the elapsed continuous battle time before clicking or reporting UI progress; once the cap is reached it invokes `GameRelaunchSubflow` with `battle_max_duration_exceeded`.

## Result

A stale `auto.png` match can no longer keep the ordinary progress watchdog alive forever. The existing game relaunch and login recovery path takes over.

## So What

Operators can tune the safety cap in `config/defaults.toml` or a profile TOML override, without introducing a CLI parameter that could be changed accidentally.

## Influence

This applies uniformly to every mode that enters `BATTLE`, including stage, dungeon, domain, and boss fights.
