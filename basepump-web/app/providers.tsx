'use client';

import type { ReactNode } from 'react';
import { PrivyProvider } from '@privy-io/react-auth';
import { base, baseSepolia } from 'viem/chains';

export default function Providers({ children }: { children: ReactNode }) {
  return (
    <PrivyProvider
      appId="cmp0oibow00gv0cl4ilo6zsyw"
      config={{
        appearance: {
          theme: 'dark',
          accentColor: '#0052FF',
          logo: 'https://i.ibb.co/placeholder/basepump-logo.png',
        },
        defaultChain: baseSepolia,
        supportedChains: [baseSepolia, base],
        loginMethods: ['google', 'twitter', 'farcaster', 'wallet'],
      }}
    >
      {children}
    </PrivyProvider>
  );
}
