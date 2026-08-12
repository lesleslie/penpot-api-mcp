# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-08-12

### Fixed

- Address ty errors
- Bypass env vars + .env lookup in test_settings
- Change ty: ignore to invalid-assignment (matches error type)
- Drop unused ty: ignore directives

### Internal

- Adopt register_http_health_route from mcp-common
- Bump oneiric dep to >=0.16.0
- Normalize LICENSE attribution to Robert Leslie and Wedgwood Web Works
- penpot-api-mcp: Migrate # type: ignore stragglers to ty syntax or fix

## [0.1.3] - 2026-06-20

### Added

- Initial implementation of penpot-api-mcp

### Internal

- Add LICENSE, README, CLAUDE.md, AGENTS.md, .gitignore
- Add mypy.ini and .cache for quality tooling
- Bump version to 0.1.1
- gitignore: Add backup file patterns to silence checkpoint tool artifacts

## [0.1.2] - 2026-06-20

### Internal

- Add mypy.ini and .cache for quality tooling
- gitignore: Add backup file patterns to silence checkpoint tool artifacts

## [0.1.1] - 2026-05-18

### Added

- Initial implementation of penpot-api-mcp

### Internal

- Add LICENSE, README, CLAUDE.md, AGENTS.md, .gitignore
