// Shared k6 helpers for rollforstore.com perf suite.
import { check } from 'k6';

export const BASE_URL = __ENV.BASE_URL || 'https://rollforstore.com';

export function checkOk(res, label) {
  return check(res, {
    [`${label}: status 200`]: (r) => r.status === 200,
    [`${label}: has body`]: (r) => r.body && r.body.length > 0,
  });
}
