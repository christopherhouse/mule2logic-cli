# Implement the I/O Module

## Task

Implement `src/core/io.js` — the module responsible for reading MuleSoft XML input.

## Requirements

- Export an async function `readInput(filePath)` that:
  - If `filePath` is provided, reads the file using `fs/promises` and returns the contents as a string.
  - If `filePath` is not provided (undefined/null), reads from stdin and returns the contents as a string.
  - Throws an error with a clear message if the file does not exist.
  - Throws an error with a clear message if the input is empty (zero-length string after trimming).

## Stdin Reading

To read from stdin, collect data chunks and resolve when stdin ends:

```js
async function readStdin() {
  const chunks = [];
  for await (const chunk of process.stdin) {
    chunks.push(chunk);
  }
  return Buffer.concat(chunks).toString("utf-8");
}
```

## Tests

Create `test/io.test.js` with tests for:
- Reading a valid file returns its contents.
- Reading a non-existent file throws an error.
- Empty input throws an error.

Create a test fixture `test/fixtures/simple-flow.xml` with the XML from spec test case 1.

Refer to `docs/mule2logic-cli-spec-v2.md` section 7 for test case XML inputs.
