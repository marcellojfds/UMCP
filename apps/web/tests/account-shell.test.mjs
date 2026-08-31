import test from "node:test";
import assert from "node:assert/strict";
import { accountIdentity, renderAccountShell } from "../src/account-shell.js";

test("account identity prefers friendly session claims and has a safe fallback", () => {
  assert.deepEqual(accountIdentity({ display_name: "Marcello Franco", email: "m@example.test" }), {
    name: "Marcello Franco",
    secondary: "m@example.test",
    initials: "MF",
  });
  assert.deepEqual(accountIdentity({ subject_id: "opaque-subject" }), {
    name: "UMCP account",
    secondary: "Personal vault",
    initials: "UA",
  });
});

test("account shell highlights the current section without exposing tenant identifiers", () => {
  const html = renderAccountShell({
    path: "/memories/example",
    title: "Memory detail",
    lede: "Inspect it.",
    session: { subject_id: "subject-secret", tenant_id: "tenant-secret" },
    content: "<p>Safe content</p>",
  });
  assert.match(html, /href="#\/memories" aria-current="page"/);
  assert.match(html, /UMCP account/);
  assert.doesNotMatch(html, /subject-secret|tenant-secret/);
});

test("account shell escapes profile claims", () => {
  const html = renderAccountShell({
    path: "/dashboard",
    title: "Today",
    session: { display_name: "<img src=x onerror=alert(1)>" },
    content: "",
  });
  assert.doesNotMatch(html, /<img/);
  assert.match(html, /&lt;img/);
});

test("account shell hides control-plane sections when the deployment is read-only", () => {
  const html = renderAccountShell({
    path: "/dashboard",
    title: "Today",
    features: { connections: false, agents: false },
    content: "",
  });
  assert.doesNotMatch(html, />Connections</);
  assert.doesNotMatch(html, />Agents</);
  assert.match(html, />Inbox</);
});
