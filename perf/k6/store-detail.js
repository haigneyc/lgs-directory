// k6 load test: /store/[id] cold-miss tolerance.
// Requires PERF_STORE_IDS env var — comma-separated store UUIDs
// representing the top 30 traffic stores. Populated from analytics.
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend } from 'k6/metrics';
import { BASE_URL } from './_lib/checks.js';

const ttfb = new Trend('ttfb_ms', true);

const RAW_IDS = __ENV.PERF_STORE_IDS || '';
const STORE_IDS = RAW_IDS.split(',').map((s) => s.trim()).filter(Boolean);

if (STORE_IDS.length === 0) {
  throw new Error('PERF_STORE_IDS env var must list at least one store UUID');
}

export const options = {
  scenarios: {
    ramp: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 10 },
        { duration: '2m', target: 30 },
        { duration: '30s', target: 0 },
      ],
      gracefulRampDown: '10s',
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<900', 'p(99)<1800'],
    http_req_failed: ['rate<0.01'],
    ttfb_ms: ['p(75)<600'],
  },
};

export default function () {
  const id = STORE_IDS[Math.floor(Math.random() * STORE_IDS.length)];
  const res = http.get(`${BASE_URL}/store/${id}`);
  ttfb.add(res.timings.waiting);
  check(res, {
    'status 200': (r) => r.status === 200,
  });
  sleep(Math.random() * 2);
}
