# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository

`ngine_io.cloudstack` — an Ansible collection for Apache CloudStack based clouds. The checkout **must** live in a directory tree ending in `ansible_collections/ngine_io/cloudstack` (it already does), otherwise `ansible-test` will not resolve the collection.

Runtime dependency is the [`cs`](https://pypi.org/project/cs/) Python library (`requirements.txt`, `cs>=3.4.0`); `meta/runtime.yml` requires ansible-core `>=2.9.10`, and CI tests against `stable-2.19`/`2.20`/`2.21`.

## Commands

Formatting (enforced by CI, `black` with `line-length = 160` from `pyproject.toml`):

```bash
black .              # format
black --check .      # what CI runs
```

Sanity tests (validates DOCUMENTATION/argspec parity, imports, licensing, …):

```bash
ansible-test sanity --docker -v --color yes
```

Integration tests run against the CloudStack simulator container. Targets are grouped by the `aliases` file in each target directory (`cloud/cs` plus `cs/group1` or `cs/group2`):

```bash
# all targets (note the trailing slash)
ansible-test integration --docker --color --diff -v cloud/cs/

# a single target (no trailing slash)
ansible-test integration --docker --color --diff -v cloud/cs/instance

# only targets affected by your changes
ansible-test integration --docker --color --diff -v --changed cloud/cs/

# a CI group
ANSIBLE_CLOUDSTACK_CONTAINER=quay.io/ansible/cloudstack-test-container:1.7.0 \
  ansible-test integration --docker -v --diff --color cs/group1/
```

`ANSIBLE_CLOUDSTACK_CONTAINER` selects the simulator image CI uses; without it `ansible-test` picks its default. Integration CI only runs on `master`, on schedule, or when a PR is labelled `automation`.

Generate the OpenAPI document from a CloudStack endpoint:

```bash
python scripts/cs_openapi.py -o cloudstack-openapi.yaml            # live endpoint
python scripts/cs_openapi.py --from-json listapis.json -o spec.yaml # offline
```

Build/install locally the way CI does:

```bash
ansible-galaxy collection build . && ansible-galaxy collection install *.tar.gz --force
```

## Architecture

### The `AnsibleCloudStack` base class

`plugins/module_utils/cloudstack.py` is the backbone: nearly every module subclasses `AnsibleCloudStack` and gets

- `self.cs` — lazily constructed `cs.CloudStack` client, and `query_api(command, **args)`, which raises through `fail_json()` on `errortext`/`CloudStackException`.
- **Resolver helpers with caching** — `get_zone()`, `get_network()`, `get_vpc()`, `get_vm()`, `get_domain()`, `get_account()`, `get_project()`, `get_ip_address()`, `get_os_type()`, `get_service_offering()`-style lookups. They translate the human-friendly module option (name) into the API's UUID, cache the result on `self.<thing>`, and accept a `key` argument to return one field. Use these instead of re-querying the API.
- **Idempotency** — `has_changed(want, current, only_keys=..., skip_diff_for_keys=...)` compares desired vs. actual and fills `self.result['diff']['before'/'after']`. Comparison is case-insensitive except for `self.case_sensitive_keys`.
- **Result shaping** — subclasses declare `self.returns = {api_key: module_return_key}` and `self.returns_to_int = {...}` in `__init__`; `get_result(resource)` merges those with `self.common_returns` (id, name, zone, state, project, account, domain, tags, …) so return values are consistent across modules. `_info` modules use the same mechanism; `get_result_and_facts()` additionally exposes `ansible_facts`.
- **Async jobs** — `poll_job(job, key)` polls `queryAsyncJobResult`; modules expose a `poll_async` option and only poll when it is true.
- **Tags** — `ensure_tags(resource, resource_type)` diffs and applies resource tags.

The API credentials argspec is shared: `cs_argument_spec()` + `cs_required_together()` in `main()`, documented via `extends_documentation_fragment: ngine_io.cloudstack.cloudstack`. Every credential option has an `env_fallback` (`CLOUDSTACK_KEY`, `CLOUDSTACK_SECRET`, `CLOUDSTACK_ENDPOINT`, `CLOUDSTACK_METHOD`, `CLOUDSTACK_TIMEOUT`, `CLOUDSTACK_VERIFY`, `CLOUDSTACK_DANGEROUS_NO_TLS_VERIFY`).

`plugins/module_utils/cloudstack_api.py` is a **separate, newer** base (`AnsibleCloudStackAPI`, subclasses `AnsibleModule`, reads credentials from `os.getenv` and supports `direct_params` so non-module plugins can use it). It is currently only used by `plugins/lookup/api.py`. Do not confuse the two — new modules follow the `AnsibleCloudStack` pattern.

### Module shape

Modules are one file per resource in `plugins/modules/`, structured as: `DOCUMENTATION` / `EXAMPLES` / `RETURN` strings → `class AnsibleCloudStack<Resource>(AnsibleCloudStack)` with `get_<resource>()`, `present_<resource>()`, `absent_<resource>()` → `main()` that builds the argspec from `cs_argument_spec()`, instantiates the class, dispatches on `state`, and `module.exit_json(**acs.get_result(resource))`. `supports_check_mode=True` is expected; guard every mutating API call with `if not self.module.check_mode`.

### Other plugins

- `plugins/inventory/instance.py` — dynamic inventory of CloudStack instances; documents credentials via the `cloudstack_environment` doc fragment (env-var mappings) and supports filters and `hostname` selection.
- `plugins/action/api_request.py` + `plugins/modules/api_request.py` — generic escape hatch to call any CloudStack API command; the action plugin folds free-form/extra task args into `params` before dispatch.
- `plugins/doc_fragments/` — `cloudstack.py` (module options) and `cloudstack_environment.py` (env-var mappings for non-module plugins).

### Integration tests

One target per module under `tests/integration/targets/<module>/`. Each target depends on the hidden `cs_common` target (`meta/main.yml`) which installs `cs`, waits for the simulator's system template, and defines shared defaults: `cs_resource_prefix` (unique per run — use it to name resources), `cs_common_template`, `cs_common_service_offering`, `cs_common_zone_adv`, `cs_common_zone_basic`. Tests are expected to cover create/idempotence/update/absent plus check mode, and to clean up after themselves.

### `scripts/`

Development tooling, excluded from the built collection via `build_ignore` in
`galaxy.yml`. It is **not** excluded from `ansible-test sanity`, which lints
every Python file in the tree — a new script must satisfy pylint (no `_` as a
variable name, no implicit string concatenation in tuples) and black.

Scripts here are controller-side only and target **Python 3.10+**, so they use
modern syntax (`match`, `X | None`, `dict[str, Any]`) that the collection's
modules cannot. `cs_openapi.py` is Apache-2.0 rather than GPL-3.0-or-later;
keep its SPDX header if you edit it.

`scripts/cs_openapi.py` converts CloudStack's proprietary `listApis` catalogue
into an OpenAPI 3.2.0 document. The mapping rules and their limits live in
[scripts/README.md](scripts/README.md); the parts worth knowing before touching
it are that CloudStack keys operations by a `command` query parameter rather
than by path (so paths are synthetic), that `listApis` describes the entity a
command returns rather than the `<command>response` envelope around it, and that
response object shapes are deduplicated into shared component schemas. The
README also covers serving the result in the official Swagger UI container,
including why **Try it out** must be disabled there.

## Adding a module

1. `plugins/modules/<name>.py` following the pattern above, with `version_added` matching the next release in `galaxy.yml`.
2. Register the module in `meta/runtime.yml` under `action_groups.cloudstack` (alphabetical).
3. Add an integration target `tests/integration/targets/<name>/` with an `aliases` file (`cloud/cs` + a `cs/groupN` line, balancing the groups) and `meta/main.yml` depending on `cs_common`. Contributions are expected to come with integration tests.
4. Add a changelog fragment in `changelogs/fragments/` (antsibull-changelog format; `CHANGELOG.rst` is generated — do not edit it by hand).
5. Run `black .` and `ansible-test sanity --docker`.

`meta/runtime.yml` also carries `plugin_routing` entries redirecting the legacy `cs_*` module names to the current ones with deprecation warnings; keep those in sync when renaming.

Releases: bump `version` in `galaxy.yml`, generate the changelog, tag, and create a GitHub release — `publish.yml` then builds and pushes to Galaxy. `docs.yml` publishes the docsite (`docs/docsite/`) to GitHub Pages.
