// Metadata is now declared on the page itself (`./page.tsx`) so the
// server-rendered shell can emit a canonical URL and OG tags. This
// layout remains as a pass-through for any future segment-level UI.

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
