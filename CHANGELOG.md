# CHANGELOG

<!-- version list -->

## v1.6.0 (2026-03-29)

### Bug Fixes

- **cache**: Classify historical finance queries as noncritical
  ([`735ff3c`](https://github.com/airuchen/financial_agent/commit/735ff3c87f712a9fc2fbd26f2af2dd5e07070174))

- **streaming**: Stabilize merged streaming and test compatibility
  ([`33f93c0`](https://github.com/airuchen/financial_agent/commit/33f93c061d5052de8609da69ed9f61281876ace2))

### Chores

- Fix ruff-format
  ([`7e4c0ff`](https://github.com/airuchen/financial_agent/commit/7e4c0fff2f57feab775e15eeea1b581b89a6299e))

### Documentation

- Factor out architecture.md
  ([`3e39ebf`](https://github.com/airuchen/financial_agent/commit/3e39ebfa78193feaf717f58b1f1d7c511a0598aa))

- Migrate documentation from doxygen to sphinx
  ([`714e749`](https://github.com/airuchen/financial_agent/commit/714e749e97b3d7e8701e7564dbc23073dd1f9f45))

- **router**: Document intent-based routing behavior
  ([`99d0f3e`](https://github.com/airuchen/financial_agent/commit/99d0f3e7fc4cc2671432e23f940a755b9f59f6af))

### Features

- **resilience**: Add retries and explicit search fallback handling
  ([`33b8bc1`](https://github.com/airuchen/financial_agent/commit/33b8bc191d6ea764d44f98ddf77611799653d29c))

- **router**: Add deterministic casual-intent guard for direct routing
  ([`a19d973`](https://github.com/airuchen/financial_agent/commit/a19d973da654d04217b7b952596ab12a742b6b8e))

- **router**: Use intent classifier with time-critical veto
  ([`aa24795`](https://github.com/airuchen/financial_agent/commit/aa247954c8bf3bfe282e6a339c8f6defb672c204))

- **security**: Harden untrusted tool-output prompt handling
  ([`af55f92`](https://github.com/airuchen/financial_agent/commit/af55f9237b76303de53ac43bb17993e17ad4048f))

- **streaming**: Implement true incremental SSE token streaming
  ([`4f19175`](https://github.com/airuchen/financial_agent/commit/4f19175bdff71d454ddfaed0ea7499d48412019b))


## v1.5.0 (2026-03-29)

### Bug Fixes

- **cache**: Classify historical finance queries as noncritical
  ([`8db09ab`](https://github.com/airuchen/financial_agent/commit/8db09ab19cb8a9b37e4fadcfc2cc4f11fb394680))

### Chores

- Fix ruff-format
  ([`aa7f26d`](https://github.com/airuchen/financial_agent/commit/aa7f26d60617af93cf8aad32f9a3739633340439))

### Documentation

- Migrate documentation from doxygen to sphinx
  ([`c6b9d9f`](https://github.com/airuchen/financial_agent/commit/c6b9d9f412b54eeffd8ebaffe75bdcf431017bfe))

### Features

- **resilience**: Add retries and explicit search fallback handling
  ([`c6ca583`](https://github.com/airuchen/financial_agent/commit/c6ca583e7eaa53753d57a48710095be6eb194006))

- **security**: Harden untrusted tool-output prompt handling
  ([`fecb369`](https://github.com/airuchen/financial_agent/commit/fecb369ff05b9fc5ab538314b543d1553a547672))


## v1.4.0 (2026-03-29)

### Documentation

- **router**: Document intent-based routing behavior
  ([`610aed0`](https://github.com/airuchen/financial_agent/commit/610aed0dd411a9cb156d97255fa4eee8b4ca7507))

### Features

- **router**: Use intent classifier with time-critical veto
  ([`9cffaea`](https://github.com/airuchen/financial_agent/commit/9cffaea42442072b350631cf1408e283fa72438b))


## v1.3.0 (2026-03-29)

### Bug Fixes

- **actions**: Always deploy docs on main updates
  ([`7521cfb`](https://github.com/airuchen/financial_agent/commit/7521cfb9fd48c74aa84f863edb112da5b3265f56))

### Features

- **router**: Add deterministic casual-intent guard for direct routing
  ([`e6e1010`](https://github.com/airuchen/financial_agent/commit/e6e101030054385f3196bad30291f5a6cc15aada))


## v1.2.3 (2026-03-29)

### Bug Fixes

- **actions**: Gate pages deploy behind repo variable
  ([`5822f1d`](https://github.com/airuchen/financial_agent/commit/5822f1dbecaadda2875730bb14fafda3cde8904c))


## v1.2.2 (2026-03-29)

### Bug Fixes

- **actions**: Enable pages site during workflow setup
  ([`ae5066c`](https://github.com/airuchen/financial_agent/commit/ae5066c8ee7b706c9a4f3a3257b9f12aac6d568c))


## v1.2.1 (2026-03-29)

### Bug Fixes

- **compose**: Use internal service hosts and robust healthchecks
  ([`0ae2271`](https://github.com/airuchen/financial_agent/commit/0ae22715d1061f3b57112eb7049440e053eaf8d7))

- **config**: Default auth to disabled for local startup
  ([`5f5bf15`](https://github.com/airuchen/financial_agent/commit/5f5bf15854a1f0e83789c8be93865b3e5a58caa5))

### Chores

- Fix pre-commit lint formatting issues
  ([`347f1c4`](https://github.com/airuchen/financial_agent/commit/347f1c4d3ec5054449e50c5244da38baf0e2068b))

- Fix pre-commit lint formatting issues
  ([`46d8082`](https://github.com/airuchen/financial_agent/commit/46d8082a971285878d8dad26d1824080b133d35d))


## v1.2.0 (2026-03-29)

### Bug Fixes

- **actions**: Configure github pages environment and setup step
  ([`dc6b588`](https://github.com/airuchen/financial_agent/commit/dc6b588c91df1395cc81d1e82e4379319fdf56d3))

### Features

- **security**: Add API key auth and Redis rate limiting
  ([`2090a43`](https://github.com/airuchen/financial_agent/commit/2090a4314efc5cf70119a7a00ba0a078e3eb5e17))


## v1.1.0 (2026-03-29)

### Bug Fixes

- **actions**: Add contents read permission for docs checkout
  ([`1183a8c`](https://github.com/airuchen/financial_agent/commit/1183a8c6822705b4b5e1f20127e0a50e24648612))

### Features

- **cache**: Add redis freshness-tiered caching with metadata
  ([`8e531e3`](https://github.com/airuchen/financial_agent/commit/8e531e344fae670cbd8f4cf6232e7828bff5ac61))


## v1.0.0 (2026-03-29)

- Initial Release
