// k6 load test: /api/stores/nearby under concurrency.
// Uses a fixed grid of US lat/lng points so results are reproducible.
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
        { duration: '30s', target: 10 },
        { duration: '2m', target: 20 },
        { duration: '30s', target: 0 },
      ],
      gracefulRampDown: '10s',
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    http_req_failed: ['rate<0.01'],
    ttfb_ms: ['p(75)<400'],
  },
};

// Fixed US metro grid — 10 points for reproducible CDN behavior.
const POINTS = [
  [33.94, -118.40], // Los Angeles
  [40.71, -74.01],  // New York
  [41.88, -87.63],  // Chicago
  [29.76, -95.37],  // Houston
  [33.45, -112.07], // Phoenix
  [39.74, -104.99], // Denver
  [25.76, -80.19],  // Miami
  [47.61, -122.33], // Seattle
  [37.77, -122.42], // San Francisco
  [42.36, -71.06],  // Boston
];

export default function () {
  const [lat, lng] = POINTS[Math.floor(Math.random() * POINTS.length)];
  const url = `${BASE_URL}/api/stores/nearby?lat=${lat}&lng=${lng}&radius=25&limit=50`;
  const res = http.get(url);
  ttfb.add(res.timings.waiting);
  check(res, {
    'status 200': (r) => r.status === 200,
    'json body': (r) => (r.headers['Content-Type'] || '').includes('json'),
  });
  sleep(Math.random() * 2);
}
