// k6 load test: rollforstore homepage steady-state baseline.
// Scenario: 0 → 100 VUs over 5 minutes.
import http from 'k6/http';
import { sleep } from 'k6';
import { Trend } from 'k6/metrics';
import { BASE_URL, checkOk } from './_lib/checks.js';

const ttfb = new Trend('ttfb_ms', true);

export const options = {
  scenarios: {
    ramp: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '1m', target: 40 },
        { duration: '3m', target: 100 },
        { duration: '1m', target: 0 },
      ],
      gracefulRampDown: '10s',
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<800', 'p(99)<1500'],
    http_req_failed: ['rate<0.01'],
    ttfb_ms: ['p(75)<500'],
  },
};

export default function () {
  const res = http.get(`${BASE_URL}/`);
  ttfb.add(res.timings.waiting);
  checkOk(res, 'homepage');
  sleep(Math.random() * 2);
}
