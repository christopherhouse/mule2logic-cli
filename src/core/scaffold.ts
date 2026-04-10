import { mkdir, writeFile } from 'fs/promises';
import { join } from 'path';
import type { ConversionModel, ConversionModelTargetApp } from './validate.js';

export async function scaffoldProject(
  model: ConversionModel,
  outputDir: string,
): Promise<void> {
  for (const app of model.target.logicAppsStandardApps) {
    const appDir = join(outputDir, app.name);
    await mkdir(appDir, { recursive: true });

    // host.json
    await writeFile(
      join(appDir, 'host.json'),
      JSON.stringify(buildHostJson(), null, 2),
      'utf-8',
    );

    // connections.json
    if (app.connections && app.connections.length > 0) {
      await writeFile(
        join(appDir, 'connections.json'),
        JSON.stringify(buildConnectionsJson(app), null, 2),
        'utf-8',
      );
    }

    // parameters.json
    const parameters = buildParametersJson(app);
    if (Object.keys(parameters).length > 0) {
      await writeFile(
        join(appDir, 'parameters.json'),
        JSON.stringify(parameters, null, 2),
        'utf-8',
      );
    }

    // Create workflow directories
    for (const workflow of app.workflows) {
      const workflowDir = join(appDir, workflow.name);
      await mkdir(workflowDir, { recursive: true });
    }
  }
}

function buildHostJson(): Record<string, unknown> {
  return {
    version: '2.0',
    extensionBundle: {
      id: 'Microsoft.Azure.Functions.ExtensionBundle.Workflows',
      version: '[1.*, 2.0.0)',
    },
  };
}

function buildConnectionsJson(app: ConversionModelTargetApp): Record<string, unknown> {
  const managedApiConnections: Record<string, unknown> = {};
  const serviceProviderConnections: Record<string, unknown> = {};

  for (const conn of app.connections) {
    const entry = {
      displayName: conn.name,
      authentication: conn.authenticationModel
        ? { type: conn.authenticationModel }
        : { type: 'Raw' },
      ...(conn.notes ? { _notes: conn.notes } : {}),
    };

    if (conn.type === 'built-in') {
      serviceProviderConnections[conn.name] = {
        parameterValues: {},
        ...entry,
      };
    } else {
      managedApiConnections[conn.name] = {
        api: { id: `TODO: resolve managed API id for ${conn.name}` },
        connection: { id: `TODO: resolve connection id for ${conn.name}` },
        ...entry,
      };
    }
  }

  return {
    ...(Object.keys(managedApiConnections).length > 0
      ? { managedApiConnections }
      : {}),
    ...(Object.keys(serviceProviderConnections).length > 0
      ? { serviceProviderConnections }
      : {}),
  };
}

function buildParametersJson(app: ConversionModelTargetApp): Record<string, unknown> {
  const params: Record<string, unknown> = {};

  if (app.appSettings) {
    for (const key of app.appSettings) {
      params[key] = {
        type: 'String',
        value: `TODO: set value for ${key}`,
      };
    }
  }

  return params;
}
