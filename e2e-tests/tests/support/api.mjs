import { expect } from "@playwright/test";
import dgram from "node:dgram";

export const env = {
  analysisBaseUrl: process.env.E2E_ANALYSIS_BASE_URL ?? "http://127.0.0.1:8010",
  sourceBaseUrl:
    process.env.E2E_TELEMETRY_SOURCE_BASE_URL ?? "http://127.0.0.1:8000",
  viewerBaseUrl: process.env.E2E_VIEWER_BASE_URL ?? "http://127.0.0.1:3001",
  streamTargetHost: process.env.E2E_STREAM_TARGET_HOST ?? "analysis-service",
  listenerBindHost: process.env.E2E_LISTENER_BIND_HOST ?? "0.0.0.0",
  listenerBasePort: Number(process.env.E2E_LISTENER_BASE_PORT ?? "14560"),
};

let sequence = 0;

export function uniqueId(prefix) {
  sequence += 1;
  return `${prefix}-${Date.now()}-${sequence}`;
}

export function listenerPort(testInfo) {
  sequence += 1;
  return env.listenerBasePort + testInfo.workerIndex * 100 + sequence;
}

export function ruleBasedProfile(overrides = {}) {
  return {
    enabled_detectors: ["rule_based"],
    ...overrides,
  };
}

export function telemetryPayload(overrides = {}) {
  return {
    timestamp: "2026-05-24T12:00:00.000Z",
    drone_id: "uav-001",
    latitude_deg: 47.397742,
    longitude_deg: 8.545594,
    altitude_m: 30,
    battery_percent: 90,
    satellites: 10,
    ground_speed_m_s: 8,
    vertical_speed_m_s: 0,
    heading_deg: 90,
    relative_altitude_m: 30,
    roll_rad: 0,
    pitch_rad: 0,
    yaw_rad: 1.5708,
    roll_rate_rad_s: 0,
    pitch_rate_rad_s: 0,
    yaw_rate_rad_s: 0,
    satellites_visible: 10,
    gps_fix_type: 3,
    gps_eph: 100,
    gps_epv: 150,
    battery_voltage_v: 12.2,
    battery_current_a: 8,
    system_status: "active",
    flight_mode: "auto",
    armed: true,
    sensor_health_flags: 4294967295,
    ...overrides,
  };
}

export async function getJson(request, url, expectedStatus = 200) {
  const response = await request.get(url);
  return readExpectedJson(response, expectedStatus);
}

export async function postJson(request, url, data, expectedStatus = 200) {
  const response = await request.post(url, { data });
  return readExpectedJson(response, expectedStatus);
}

export async function deleteJson(request, url, expectedStatus = 200) {
  const response = await request.delete(url);
  return readExpectedJson(response, expectedStatus);
}

export async function sendUdpPacket(host, port, payload) {
  const socket = dgram.createSocket("udp4");
  const message = Buffer.isBuffer(payload) ? payload : Buffer.from(payload);

  try {
    await new Promise((resolve, reject) => {
      socket.send(message, port, host, (error) => {
        if (error) {
          reject(error);
        } else {
          resolve();
        }
      });
    });
  } finally {
    socket.close();
  }
}

export async function readExpectedJson(response, expectedStatus) {
  const text = await response.text();
  const payload = parsePayload(text);
  expect(
    response.status(),
    `${response.url()} returned ${response.status()} ${response.statusText()}: ${text}`,
  ).toBe(expectedStatus);
  return payload;
}

export async function createAnalysisSession(request, options = {}) {
  const sessionId = options.sessionId ?? uniqueId("analysis-session");
  const body = {
    session_id: sessionId,
    drone_id: options.droneId ?? "uav-001",
    profile: options.profile ?? ruleBasedProfile(),
  };
  const session = await postJson(
    request,
    `${env.analysisBaseUrl}/analysis/sessions`,
    body,
    201,
  );
  return { sessionId, session };
}

export async function analyzeTelemetry(request, sessionId, telemetry) {
  return postJson(
    request,
    `${env.analysisBaseUrl}/analysis/sessions/${sessionId}/analyze`,
    {
      format: "unified.telemetry",
      telemetry,
    },
  );
}

export async function createListener(request, sessionId, port) {
  return postJson(
    request,
    `${env.analysisBaseUrl}/analysis/listeners`,
    {
      session_id: sessionId,
      protocol: "udp",
      format: "mavlink.v2",
      bind_host: env.listenerBindHost,
      bind_port: port,
      buffer_size: 4096,
    },
    201,
  );
}

export async function createMission(request, name = uniqueId("mission")) {
  return postJson(
    request,
    `${env.sourceBaseUrl}/sources/synthetic/missions`,
    missionPayload(name),
    201,
  );
}

export async function startSyntheticUdpStream(request, missionId, port) {
  return postJson(
    request,
    `${env.sourceBaseUrl}/streams/synthetic/missions/${missionId}/udp`,
    {
      host: env.streamTargetHost,
      port,
      frequency_hz: 20,
    },
    201,
  );
}

export async function injectAnomaly(request, missionId, anomalyType) {
  return postJson(
    request,
    `${env.sourceBaseUrl}/sources/synthetic/missions/${missionId}/commands`,
    {
      command: "inject_anomaly",
      type: anomalyType,
      start_after_sec: 0,
      duration_sec: 5,
      intensity: 1,
    },
  );
}

export async function startPipeline(request, testInfo, options = {}) {
  const resources = {
    sessionId: options.sessionId ?? uniqueId("pipeline-session"),
    listenerId: null,
    missionId: null,
    streamId: null,
    port: options.port ?? listenerPort(testInfo),
  };

  try {
    await createAnalysisSession(request, {
      sessionId: resources.sessionId,
      profile: options.profile ?? ruleBasedProfile(),
    });

    const listener = await createListener(
      request,
      resources.sessionId,
      resources.port,
    );
    resources.listenerId = listener.listener_id;

    await waitForValue(
      async () =>
        getJson(
          request,
          `${env.analysisBaseUrl}/analysis/listeners/${resources.listenerId}`,
        ),
      (payload) => payload.status === "active",
      "listener to become active",
    );

    const mission = await createMission(request);
    resources.missionId = mission.mission_id;

    const stream = await startSyntheticUdpStream(
      request,
      resources.missionId,
      resources.port,
    );
    resources.streamId = stream.stream_id;

    return resources;
  } catch (error) {
    await cleanupPipeline(request, resources);
    throw error;
  }
}

export async function cleanupPipeline(request, resources) {
  if (resources.streamId) {
    await deleteIfExists(
      request,
      `${env.sourceBaseUrl}/streams/udp/${resources.streamId}`,
    );
  }
  if (resources.listenerId) {
    await deleteIfExists(
      request,
      `${env.analysisBaseUrl}/analysis/listeners/${resources.listenerId}`,
    );
  }
  if (resources.sessionId) {
    await deleteIfExists(
      request,
      `${env.analysisBaseUrl}/analysis/sessions/${resources.sessionId}`,
    );
  }
}

export async function waitForListenerSamples(request, listenerId) {
  return waitForValue(
    async () =>
      getJson(request, `${env.analysisBaseUrl}/analysis/listeners/${listenerId}`),
    (payload) => payload.received_packets > 0 && payload.converted_samples > 0,
    "listener samples",
  );
}

export async function waitForLastResult(
  request,
  sessionId,
  predicate,
  options = {},
) {
  return waitForValue(
    async () => {
      const payload = await getJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${sessionId}/last-result`,
      );
      return payload.result;
    },
    (result) => Boolean(result) && predicate(result),
    "session last result",
    options.timeoutMs ?? 20_000,
    options.intervalMs ?? 250,
  );
}

export async function waitForSessionState(request, sessionId, predicate) {
  return waitForValue(
    async () =>
      getJson(
        request,
        `${env.analysisBaseUrl}/analysis/sessions/${sessionId}/state`,
      ),
    predicate,
    "session state",
    20_000,
  );
}

export async function waitForValue(
  load,
  predicate,
  description,
  timeoutMs = 15_000,
  intervalMs = 250,
) {
  const startedAt = Date.now();
  let lastValue = null;

  while (Date.now() - startedAt < timeoutMs) {
    lastValue = await load();
    if (predicate(lastValue)) {
      return lastValue;
    }
    await delay(intervalMs);
  }

  throw new Error(
    `Timed out waiting for ${description}. Last value: ${JSON.stringify(lastValue)}`,
  );
}

export function anomalyTypes(result) {
  return result.anomalies.map((anomaly) => anomaly.type);
}

export function findAnomaly(result, type) {
  return result.anomalies.find((anomaly) => anomaly.type === type);
}

function missionPayload(name) {
  return {
    name,
    frequency_hz: 20,
    drone_id: "uav-001",
    home: {
      latitude: 47.397742,
      longitude: 8.545594,
      altitude: 0,
      heading_deg: 90,
      battery: 100,
    },
    steps: [
      { type: "takeoff", target_altitude: 30 },
      { type: "move_forward", distance_m: 500, speed_m_s: 8 },
      { type: "hover", duration_sec: 60 },
      { type: "landing" },
    ],
    noise_profile: {
      random_seed: 7,
      gps_position_std_m: 0,
      altitude_std_m: 0,
      speed_std_m_s: 0,
      heading_std_deg: 0,
      battery_std_percent: 0,
    },
  };
}

async function deleteIfExists(request, url) {
  const response = await request.delete(url);
  if (![200, 404].includes(response.status())) {
    await readExpectedJson(response, 200);
  }
}

function parsePayload(text) {
  if (!text) {
    return null;
  }
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function delay(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}
