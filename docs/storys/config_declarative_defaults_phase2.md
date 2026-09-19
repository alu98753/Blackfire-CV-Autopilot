# Config Declarative Defaults

The repository stores shared configuration in `config/defaults.toml`.

User-specific overrides belong in:

```text
user_data/<profile>/config.toml
```

The active profile override is merged on top of the repository defaults. If it
does not exist, the application uses `config/defaults.toml` directly.

Profile configuration is local user data and must not be committed to Git.
