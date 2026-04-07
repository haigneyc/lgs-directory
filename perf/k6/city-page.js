// k6 load test: /stores/[state]/[city] ISR hit-rate validation.
// Scenario: 0 → 50 VUs over 3 minutes across 5 representative cities.
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend } from 'k6/metrics';
import { BASE_URL } from './_lib/checks.js';

const ttfb = new Trend('ttfb_ms', true);

export const options = {
  scenarios: {
    ramp: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 20 },
        { duration: '2m', target: 50 },
        { duration: '30s', target: 0 },
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

const CITIES = [
  ['california', 'los-angeles'],
  ['texas', 'houston'],
  ['new-york', 'new-york'],
  ['florida', 'miami'],
  ['illinois', 'chicago'],
];

export default function () {
  const [state, city] = CITIES[Math.floor(Math.random() * CITIES.length)];
  const res = http.get(`${BASE_URL}/stores/${state}/${city}`);
  ttfb.add(res.timings.waiting);
  check(res, {
    'status 200': (r) => r.status === 200,
    'has store list': (r) => r.body.includes('Game Stores in'),
  });
  sleep(Math.random() * 2);
}
