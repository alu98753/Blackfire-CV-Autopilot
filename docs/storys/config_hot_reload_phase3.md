# Profile Configuration and Hot Reload

Runtime configuration uses two layers:

```text
config/defaults.toml
    ↓
user_data/<profile>/config.toml
```

`config/defaults.toml` is the versioned shared baseline. The active profile
file is optional and contains only user-specific overrides. Profiles without
an override file continue to use the shared defaults.

Configuration changes written through the CLI are saved to the active profile
file and can be applied by the existing runtime refresh flow. Runtime logs,
incident records, and daily status remain under the same profile directory.
