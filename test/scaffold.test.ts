import { describe, it, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { readFile, rm, stat } from 'node:fs/promises';
import { join } from 'node:path';
import { mkdtemp } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { scaffoldProject } from '../src/core/scaffold.js';
import type { ConversionModel } from '../src/core/validate.js';

const minimalModel: ConversionModel = {
  assessmentVersion: '1.0',
  source: {
    rootPath: '/test',
    applications: [{
      name: 'test-app',
      files: [],
      flows: [],
      dependencies: [],
      transforms: [],
    }],
  },
  target: {
    logicAppsStandardApps: [{
      name: 'my-logic-app',
      workflows: [
        {
          name: 'HelloFlow',
          sourceArtifacts: ['src/main/mule/flow.xml'],
          trigger: { type: 'Request' },
          actionsSummary: ['Compose'],
          recommendedImplementation: 'workflow',
          riskLevel: 'low',
        },
        {
          name: 'HealthCheck',
          sourceArtifacts: ['src/main/mule/flow.xml'],
          trigger: { type: 'Request' },
          actionsSummary: ['Compose'],
          recommendedImplementation: 'workflow',
          riskLevel: 'low',
        },
      ],
      connections: [
        {
          name: 'http',
          type: 'built-in',
          sourceConfigs: ['HTTP_Listener_config'],
          authenticationModel: 'Anonymous',
        },
        {
          name: 'sql',
          type: 'managed',
          sourceConfigs: ['Database_Config'],
          authenticationModel: 'Raw',
        },
      ],
      appSettings: ['http.port', 'api.basePath'],
    }],
  },
  executionPlan: {
    phases: [{
      phase: 1,
      name: 'Discovery',
      tasks: [{ id: 'P1-T1', title: 'Scan files' }],
    }],
  },
};

let tempDir: string;

describe('scaffoldProject', () => {
  afterEach(async () => {
    if (tempDir) {
      await rm(tempDir, { recursive: true, force: true });
    }
  });

  it('creates the app directory', async () => {
    tempDir = await mkdtemp(join(tmpdir(), 'scaffold-test-'));
    await scaffoldProject(minimalModel, tempDir);
    const appDir = join(tempDir, 'my-logic-app');
    const s = await stat(appDir);
    assert.ok(s.isDirectory());
  });

  it('creates host.json', async () => {
    tempDir = await mkdtemp(join(tmpdir(), 'scaffold-test-'));
    await scaffoldProject(minimalModel, tempDir);
    const hostJson = JSON.parse(
      await readFile(join(tempDir, 'my-logic-app', 'host.json'), 'utf-8'),
    );
    assert.equal(hostJson.version, '2.0');
    assert.ok(hostJson.extensionBundle);
  });

  it('creates connections.json with built-in and managed connections', async () => {
    tempDir = await mkdtemp(join(tmpdir(), 'scaffold-test-'));
    await scaffoldProject(minimalModel, tempDir);
    const connJson = JSON.parse(
      await readFile(join(tempDir, 'my-logic-app', 'connections.json'), 'utf-8'),
    );
    assert.ok(connJson.serviceProviderConnections?.http, 'Should have built-in connection');
    assert.ok(connJson.managedApiConnections?.sql, 'Should have managed connection');
  });

  it('creates parameters.json from appSettings', async () => {
    tempDir = await mkdtemp(join(tmpdir(), 'scaffold-test-'));
    await scaffoldProject(minimalModel, tempDir);
    const params = JSON.parse(
      await readFile(join(tempDir, 'my-logic-app', 'parameters.json'), 'utf-8'),
    );
    assert.ok(params['http.port']);
    assert.ok(params['api.basePath']);
  });

  it('creates workflow directories', async () => {
    tempDir = await mkdtemp(join(tmpdir(), 'scaffold-test-'));
    await scaffoldProject(minimalModel, tempDir);
    const helloDir = await stat(join(tempDir, 'my-logic-app', 'HelloFlow'));
    assert.ok(helloDir.isDirectory());
    const healthDir = await stat(join(tempDir, 'my-logic-app', 'HealthCheck'));
    assert.ok(healthDir.isDirectory());
  });

  it('skips connections.json when no connections', async () => {
    const noConnModel: ConversionModel = {
      ...minimalModel,
      target: {
        logicAppsStandardApps: [{
          ...minimalModel.target.logicAppsStandardApps[0],
          connections: [],
          appSettings: undefined,
        }],
      },
    };
    tempDir = await mkdtemp(join(tmpdir(), 'scaffold-test-'));
    await scaffoldProject(noConnModel, tempDir);
    await assert.rejects(
      stat(join(tempDir, 'my-logic-app', 'connections.json')),
    );
  });
});
