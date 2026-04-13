# Sample Projects

Representative MuleSoft projects and individual flow XML files used for testing and validation.

## Contents

### `hello-world-project/`
A minimal but representative MuleSoft project with:
- `pom.xml` — Maven project with HTTP and DB connector dependencies
- `mule-artifact.json` — Mule artifact metadata
- `src/main/mule/hello-flow.xml` — Flows with HTTP listener, transforms, error handlers
- `src/main/mule/shared-subflow.xml` — Reusable sub-flows
- `src/main/mule/global-config.xml` — Global connector configurations
- `src/main/resources/application.properties` — Property placeholders
- `src/main/resources/application-dev.properties` — Dev environment overrides

### `standalone-flow.xml`
A standalone Mule XML file with external references (config-refs, property placeholders, flow-refs to undefined targets). Used for single-flow mode testing.

### `malformed-flow.xml`
Invalid XML for error-handling tests.

### `empty-flow.xml`
Valid XML with no `<flow>` or `<sub-flow>` elements.
