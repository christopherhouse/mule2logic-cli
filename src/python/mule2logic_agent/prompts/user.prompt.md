Convert the following MuleSoft XML to Azure Logic Apps Standard workflow JSON.

Before converting, use the Context7 MCP server to research the MuleSoft components in this XML — resolve MuleSoft library IDs and query documentation for any connectors, processors, or patterns you find. This ensures you understand the exact semantics of the source flow.

Then use the Microsoft Learn MCP server to look up Azure Logic Apps schema details, trigger/action definitions, and best practices to ensure the output is valid.

Both MCP servers should always be consulted.

<mulesoft-xml>
{{xml}}
</mulesoft-xml>

REMEMBER: Your final response MUST be ONLY the raw JSON object. No explanation, no summary, no markdown, no commentary. The very first character must be { and the very last character must be }. Any text outside the JSON will cause a fatal parse error.
