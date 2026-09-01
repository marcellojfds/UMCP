const navigation = Object.freeze([
  ["/dashboard", "Today", "home"],
  ["/memories", "Memories", "memory"],
  ["/inbox", "Inbox", "inbox"],
  ["/connections", "Connections", "connection"],
  ["/agents", "Agents", "agent"],
]);

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
  })[character]);
}

function initials(value) {
  const words = String(value || "U").trim().split(/\s+/).filter(Boolean);
  return words.slice(0, 2).map((word) => word[0]).join("").toUpperCase() || "U";
}

export function accountIdentity(session = {}) {
  const name = session.display_name || session.name || session.email || "UMCP account";
  const secondary = session.email && session.email !== name ? session.email : "Personal vault";
  return Object.freeze({ name: String(name), secondary: String(secondary), initials: initials(name) });
}

function navIcon(kind) {
  const paths = {
    home: '<path d="M3 10.5 10 4l7 6.5V18H6v-7.5Z"/><path d="M8.5 18v-5h3v5"/>',
    memory: '<rect x="4" y="3" width="12" height="14" rx="2"/><path d="M7 7h6M7 10h6M7 13h4"/>',
    inbox: '<path d="M3 11h4l2 3h2l2-3h4"/><path d="m5 5-2 6v6h14v-6l-2-6Z"/>',
    connection: '<circle cx="6" cy="10" r="3"/><circle cx="14" cy="6" r="2"/><circle cx="14" cy="15" r="2"/><path d="m8.5 8.5 3.6-1.7M8.7 11.4l3.5 2.4"/>',
    agent: '<rect x="4" y="6" width="12" height="10" rx="3"/><path d="M10 3v3M7.5 11h.01M12.5 11h.01M8 14h4"/>',
    settings: '<circle cx="10" cy="10" r="3"/><path d="M10 2.5v2m0 11v2m-5.3-2.2 1.4-1.4m7.8-7.8 1.4-1.4M2.5 10h2m11 0h2m-2.2 5.3-1.4-1.4M6.1 6.1 4.7 4.7"/>',
  };
  return `<svg aria-hidden="true" viewBox="0 0 20 20">${paths[kind] || paths.home}</svg>`;
}

export function renderAccountShell({ path, title, lede = "", session = {}, content, toolbar = "", features = {} }) {
  const identity = accountIdentity(session);
  const visibleNavigation = navigation.filter(([href]) => (href !== "/connections" || features.connections !== false) && (href !== "/agents" || features.agents !== false));
  const links = visibleNavigation.map(([href, label, icon]) => {
    const active = path === href || (href === "/memories" && path.startsWith("/memories/"));
    return `<a class="account-nav__link${active ? " is-active" : ""}" href="#${href}"${active ? ' aria-current="page"' : ""}>${navIcon(icon)}<span>${label}</span></a>`;
  }).join("");
  const isSettingsActive = path === "/settings/security";
  return `<div class="account-app">
    <aside class="account-sidebar">
      <a class="account-brand" href="#/dashboard" aria-label="UMCP home"><span class="account-brand__mark">U</span><span>UMCP<small>Memory vault</small></span></a>
      <nav class="account-nav" aria-label="Account navigation">${links}<a class="account-nav__link account-nav__link--mobile-only${isSettingsActive ? " is-active" : ""}" href="#/settings/security"${isSettingsActive ? ' aria-current="page"' : ""}>${navIcon("settings")}<span>Settings</span></a></nav>
      <div class="account-sidebar__spacer"></div>
      <a class="account-nav__link account-nav__link--desktop-only${isSettingsActive ? " is-active" : ""}" href="#/settings/security"${isSettingsActive ? ' aria-current="page"' : ""}>${navIcon("settings")}<span>Settings</span></a>
      <details class="account-profile">
        <summary><span class="account-avatar">${escapeHtml(identity.initials)}</span><span class="account-profile__copy"><strong>${escapeHtml(identity.name)}</strong><small>${escapeHtml(identity.secondary)}</small></span><span aria-hidden="true">•••</span></summary>
        <div class="account-profile__menu"><a href="#/settings/security">Account &amp; security</a>${features.connections === false ? "" : '<a href="#/connections">Manage connections</a>'}<button type="button" data-account-logout>Log out</button></div>
      </details>
    </aside>
    <section class="account-workspace">
      <header class="account-topbar"><a class="account-mobile-brand" href="#/dashboard">UMCP</a><form class="vault-search" role="search"><label class="sr-only" for="vault-search-input">Search your memories</label><span aria-hidden="true">⌕</span><input id="vault-search-input" name="query" type="search" placeholder="Search your memories…" autocomplete="off"><kbd>⌘ K</kbd><button class="sr-only" type="submit">Search memories</button></form><span class="vault-label">Personal vault</span></header>${session.preview_mode ? '<div class="account-preview-banner" role="status"><strong>Local preview</strong><span>Sample data only · actions do not affect your vault</span></div>' : ""}
      <main class="account-main" id="account-main"><header class="account-page-header"><div><p class="account-eyebrow">Personal vault</p><h1>${escapeHtml(title)}</h1>${lede ? `<p>${escapeHtml(lede)}</p>` : ""}</div>${toolbar}</header>${content}</main>
    </section>
  </div>`;
}

export const accountNavigation = navigation;
