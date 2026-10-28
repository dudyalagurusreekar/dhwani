"use client";

import DhwaniSphere from "./DhwaniSphere";

// Re-export DhwaniSphere as default to guarantee backwards compatibility
// and prevent any cached component from displaying the old balloon geometry
export default function Hero3DOrb(props: React.ComponentProps<typeof DhwaniSphere>) {
  return <DhwaniSphere {...props} />;
}
