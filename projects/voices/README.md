# Voice Profiles

Voice profiles are stored as YAML and resolved independently of speaker IDs.

- `id`: voice profile id
- `engine`: TTS engine name
- `reference`: optional sample audio path
- `parameters`: `pitch`, `speaking_rate`, `gain_db`
- `style`: arbitrary style metadata such as `personality` and `energy`

At runtime, a manifest maps `speaker -> character -> voice`, and the selected voice id is resolved from the character's `voice` field.
