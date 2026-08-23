# Repository scripts

Development tooling for this collection. Nothing in this directory is part of
the published collection — `galaxy.yml` excludes it from the build.

## `cs_openapi.py`

Generates an **OpenAPI 3.2.0** document from CloudStack's `listApis` command.

```bash
# against the endpoint from ~/.cloudstack.ini or the CLOUDSTACK_* env variables
./scripts/cs_openapi.py -o cloudstack-openapi.yaml

# resolve response payload keys exactly by probing read-only list commands
./scripts/cs_openapi.py --probe-response-keys -o cloudstack-openapi.yaml

# offline, from a captured listApis response
./scripts/cs_openapi.py --from-json listapis.json -o cloudstack-openapi.json
```

Requires the `cs` library for live sources (already in `requirements.txt`) and
PyYAML for YAML output; `--format json` needs neither beyond `cs`.

Useful flags: `--endpoint` overrides the configured endpoint, `--dump-listapis`
saves the raw response for offline re-runs, `--server-url` sets the advertised
server, `--api-version` overrides `info.version` (which otherwise comes from
`listCapabilities`), and `--self` sets the OpenAPI 3.2 `$self` field.

Output is deterministic: the same `listApis` response always produces a
byte-identical document.

### Browsing the result in Swagger UI

The generated document is served as-is by the official Swagger UI container,
following the [Swagger UI installation
docs](https://github.com/swagger-api/swagger-ui/blob/HEAD/docs/usage/installation.md).
Put the document in a directory of its own and mount that directory:

```bash
mkdir -p /tmp/cs-spec
./scripts/cs_openapi.py --probe-response-keys -o /tmp/cs-spec/cloudstack-openapi.yaml

docker run --rm -p 8088:8080 \
  -e SWAGGER_JSON=/spec/cloudstack-openapi.yaml \
  -v /tmp/cs-spec:/spec \
  docker.io/swaggerapi/swagger-ui
```

Then open <http://localhost>. `SWAGGER_JSON` takes YAML as happily as JSON
despite its name — the entrypoint copies the file next to the bundle and points
Swagger UI at it. On a rootless container runtime, publish an unprivileged port
(`-p 8080:8080`) instead of `80`, and add `:ro,Z` to the volume if SELinux is
enforcing. `docker.swagger.io` proxies Docker Hub and can answer with
`toomanyrequests`; `docker.io/swaggerapi/swagger-ui` is the same image and is a
usable fallback.

OpenAPI 3.2 needs a recent Swagger UI: support landed across the Swagger
tooling in April 2026, and the `latest` image renders the document with an
"OAS 3.2" badge. Verified with swagger-ui 5.32.14 against a CloudStack
4.22.0.0 catalogue: 815 operations and 310 tags, no console errors.

With 815 operations the defaults are unpleasant, so a few settings are worth
adding:

```bash
docker run --rm -p 8088:8080 \
  -e SWAGGER_JSON=/spec/cloudstack-openapi.yaml \
  -e DOC_EXPANSION=none \
  -e FILTER=true \
  -e SHOW_EXTENSIONS=true \
  -e SUPPORTED_SUBMIT_METHODS='[]' \
  -v /tmp/cs-spec:/spec \
  docker.io/swaggerapi/swagger-ui
```

- `DOC_EXPANSION=none` collapses the tag groups, so the page opens on a table of
  contents rather than 815 expanded rows.
- `FILTER=true` adds the search box, which is the practical way to find a
  command.
- `SHOW_EXTENSIONS=true` surfaces the `x-cloudstack-*` annotations —
  `x-cloudstack-since`, `x-cloudstack-related`, `x-cloudstack-async` — next to
  the parameters they describe.
- `SUPPORTED_SUBMIT_METHODS='[]'` removes the **Try it out** button. This one is
  not cosmetic: see below.

**Try it out does not work, by construction.** Swagger UI builds the request URL
by appending the path to the server URL, so it sends
`…/client/api/listZones?command=listZones` — the synthetic path segment is real
to the browser even though CloudStack has no such route. The container exposes
no request-interceptor hook to strip it, so the honest configuration is to turn
the button off and treat the page as a reference. Two further blockers apply
even with the URL corrected: CloudStack expects an HMAC `signature` the browser
cannot compute, and it does not send CORS headers to a page on another origin.

To serve the document from somewhere else instead of mounting it, use
`SWAGGER_JSON_URL=https://host/cloudstack-openapi.yaml`; that endpoint has to
allow cross-origin reads.

### How CloudStack concepts are mapped

**Operations.** CloudStack has a single endpoint and selects the command with a
`command` query parameter, which OpenAPI cannot express — a path may not carry a
query string, and one path item holds only one `get`. Each command therefore
becomes a synthetic path named after it (`/listZones`) plus a required `command`
parameter pinned with `const`. Requests really go to the server URL with
`?command=…`; the path segment is a naming device and is called out in
`info.description`. `operationId` is the command name.

**Parameters.** Every `listApis` parameter becomes a query parameter. `list`
types are serialised comma-separated (`style: form`, `explode: false`). `map`
types carry `x-cloudstack-encoding: indexed-map`, because CloudStack expects
`tags[0].key=k&tags[0].value=v` rather than any standard OpenAPI style. The
`length` of a string parameter becomes `maxLength`.

**Responses.** Every body is wrapped by CloudStack in a single
`<command>response` key, which the schemas reproduce. Errors reuse that same key
and repeat their `errorcode` in the HTTP status, so they are modelled as the
`default` response.

**Payload keys.** `listApis` documents the *entity* a command deals with, never
the envelope around it, and CloudStack returns that entity in one of three ways:
directly (`{"success": true}`), nested under a command-specific key
(`{"zone": {…}}`), or as a counted array (`{"count": 1, "zone": [{…}]}`). That
key is not part of `listApis`. By default the schema stays open enough to
validate all three; `--probe-response-keys` calls the read-only `list*` commands
on a live endpoint and pins the real key where the endpoint returns data.

**Asynchronous commands.** These return only `{"jobid": …, "id": …}`, so that is
what the `200` schema describes. The documented entity — which arrives later in
the `jobresult` of `queryAsyncJobResult` — is referenced from
`x-cloudstack-jobresult-schema`.

**Schemas.** Response objects repeat across commands: 1376 objects in a 4.22
catalogue collapse into ~255 distinct shapes, so identical shapes are emitted
once and shared. A shape is named after the field that carries it (`Nic`,
`Tags`) or, for top-level shapes, after the entity the commands using it agree
on (`VirtualMachine`, `Volume`). The `{success, displaytext}` shape that 203
delete-style commands share is named `SuccessResult`.

**Tags.** Commands are grouped by the entity in their name, with the verb
stripped. Entities shared by several commands act as anchors, so
`addNicToVirtualMachine` joins `VirtualMachine` rather than forming a group of
its own. Tags are cosmetic grouping only.

**Types.** CloudStack scalars map to the obvious OpenAPI types; `uuid` gains
`format: uuid`. A `list` or `set` field whose element shape `listApis` does not
document keeps unconstrained items, because such fields do carry objects in
practice (`Template.downloaddetails`). Dates stay plain strings because CloudStack renders them as
`2026-07-29T11:18:10+0000`, which is ISO 8601 but not RFC 3339, so `format:
date-time` would be wrong. Types with no OpenAPI equivalent — enum-like names
such as `powerstate`, or nested `*response` types — keep their original name in
`x-cloudstack-type`.

### Known limits

- Only `GET` is described, though CloudStack accepts `POST` with the same
  parameters.
- `listApis` reflects what the *calling account* may see, so an operator key and
  a user key produce different documents.
- Enum-like types carry no value list; `listApis` does not publish one.
- `listApis` occasionally lists a parameter twice and pads response field lists
  with empty objects; both are cleaned up during generation.
