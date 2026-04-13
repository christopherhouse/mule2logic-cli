---
name: mulesoft-project
description: "MuleSoft Anypoint project layout, Mule XML flow conventions, pom.xml structure, connector configs, property files. Use when parsing Mule projects, understanding flow XML, or building sample fixtures."
---

# MuleSoft / Anypoint Project Conventions

## When to Use

- Parsing or analyzing Mule project input
- Understanding Mule flow XML structure
- Building sample Mule fixtures for testing
- Handling single-flow mode edge cases

## Project Layout

A standard MuleSoft/Anypoint project:

```
<project-root>/
├── pom.xml
├── mule-artifact.json
└── src/
    └── main/
        ├── mule/
        │   ├── <flow-name>.xml
        │   ├── <another-flow>.xml
        │   └── global-config.xml
        └── resources/
            ├── application.properties
            ├── application-dev.properties
            └── log4j2.xml
```

### pom.xml

Identifies dependencies, connectors, and Mule runtime version. Key elements:

- `<groupId>`, `<artifactId>`, `<version>` — project coordinates
- `<dependencies>` — connectors used (e.g., `mule-http-connector`, `mule-db-connector`)
- `<mule.version>` or parent POM — runtime version

### mule-artifact.json

Metadata about the deployable artifact. Contains `minMuleVersion` and classifier info.

## Mule Flow XML Structure

Each `.xml` file under `src/main/mule/` contains flows:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mule xmlns="http://www.mulesoft.org/schema/mule/core"
      xmlns:http="http://www.mulesoft.org/schema/mule/http"
      xmlns:db="http://www.mulesoft.org/schema/mule/db"
      xmlns:ee="http://www.mulesoft.org/schema/mule/ee/core">

    <!-- Global configs (often in separate file) -->
    <http:listener-config name="HTTP_Listener_config">
        <http:listener-connection host="0.0.0.0" port="8081"/>
    </http:listener-config>

    <!-- Flow -->
    <flow name="myFlow">
        <http:listener config-ref="HTTP_Listener_config" path="/api"/>
        <ee:transform>
            <ee:message>
                <ee:set-payload><![CDATA[%dw 2.0 output application/json --- { ... }]]></ee:set-payload>
            </ee:message>
        </ee:transform>
        <http:request method="POST" url="https://example.com/api"/>
        <error-handler>
            <on-error-propagate type="HTTP:CONNECTIVITY">
                <set-payload value="Connection error"/>
            </on-error-propagate>
        </error-handler>
    </flow>

    <!-- Sub-flow (reusable, no trigger) -->
    <sub-flow name="sharedLogic">
        <set-variable variableName="status" value="processed"/>
    </sub-flow>
</mule>
```

## Key XML Elements

### Triggers (first element in a flow)

| Element | Namespace | Maps To |
|---------|-----------|---------|
| `<http:listener>` | `http` | Request trigger |
| `<scheduler>` | core | Recurrence trigger |
| `<jms:listener>` | jms | Service Bus trigger |
| `<file:listener>` | file | File trigger |

### Processors

| Element | Namespace | Maps To |
|---------|-----------|---------|
| `<set-payload>` | core | Compose / Set body |
| `<set-variable>` | core | SetVariable |
| `<flow-ref>` | core | Scope / internal call |
| `<http:request>` | http | HTTP action |
| `<db:select>`, `<db:insert>` | db | SQL action |
| `<ee:transform>` | ee | DataWeave transform |

### Routers

| Element | Maps To |
|---------|---------|
| `<choice>` | Condition / Switch |
| `<foreach>` | Foreach |
| `<scatter-gather>` | Parallel branches |

### Error Handling

| Element | Maps To |
|---------|---------|
| `<error-handler>` | Scope with runAfter |
| `<on-error-propagate>` | Error re-throw |
| `<on-error-continue>` | Error suppression |

## Single-Flow Mode Considerations

When processing a standalone `.xml` file:

- No `pom.xml` — cannot resolve connector versions from dependencies.
- Global configs (e.g., `<http:listener-config>`) may be defined in other files — emit warnings for `config-ref` attributes pointing to undefined configs.
- Property placeholders (`${property.name}`) may be unresolvable — emit warnings.
- The file must contain at least one `<flow>` or `<sub-flow>` element to be valid input.

## Property References

Mule uses `${property.name}` syntax, resolved from:
- `application.properties`
- Environment-specific property files
- System properties
- In single-flow mode, these are typically unresolvable → emit warnings.
