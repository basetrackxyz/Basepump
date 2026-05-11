'use client';

import { usePrivy } from '@privy-io/react-auth';
import { useEffect, useState } from 'react';

interface Token {
  address: string;
  creator: string;
  name: string;
  symbol: string;
  total_supply: number;
  eth_collected: number;
}

export default function Home() {
  const { ready, authenticated, login, logout, user } = usePrivy();
  const [tokens, setTokens] = useState<Token[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/tokens')
      .then((res) => res.json())
      .then((data) => setTokens(data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (!ready) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-blue-500 text-xl animate-pulse">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black text-white">
      <header className="border-b border-gray-800 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-2xl font-bold text-blue-500">Base</span>
          <span className="text-2xl font-bold text-cyan-400">Pump</span>
        </div>
        <div className="flex gap-2">
          {authenticated ? (
            <div className="flex items-center gap-3">
              <span className="text-gray-400 text-sm hidden sm:block">
                {user?.wallet?.address ? `${user.wallet.address.slice(0, 6)}...${user.wallet.address.slice(-4)}` : 'Connected'}
              </span>
              <button
                onClick={() => (window.location.href = '/create')}
                className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg text-sm font-medium"
              >
                + Create
              </button>
              <button
                onClick={logout}
                className="border border-gray-700 px-3 py-2 rounded-lg text-sm text-gray-400 hover:text-white"
              >
                Logout
              </button>
            </div>
          ) : (
            <button
              onClick={login}
              className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg text-sm font-medium"
            >
              Connect
            </button>
          )}
        </div>
      </header>

      <div className="px-4 py-8 text-center">
        <h1 className="text-3xl sm:text-5xl font-bold mb-3">
          Launch tokens on <span className="text-blue-500">Base</span>
        </h1>
        <p className="text-gray-400 text-lg">Bonding curve. Fair launch. No presale.</p>
      </div>

      <div className="px-4 max-w-6xl mx-auto">
        <h2 className="text-xl font-semibold mb-4 text-gray-200">🔥 Live Tokens</h2>
        {loading ? (
          <div className="text-center text-gray-500 py-12">Loading tokens...</div>
        ) : tokens.length === 0 ? (
          <div className="text-center text-gray-500 py-12">
            No tokens yet.{' '}
            <a href="/create" className="text-blue-500 hover:underline">
              Be the first!
            </a>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {tokens.map((token) => {
              const progress = Math.min((token.eth_collected / 24) * 100, 100);
              return (
                <a
                  key={token.address}
                  href={`/token/${token.address}`}
                  className="border border-gray-800 rounded-xl p-4 hover:border-blue-500 transition-colors bg-gray-900"
                >
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center font-bold text-sm">
                      {token.symbol?.slice(0, 2)}
                    </div>
                    <div>
                      <div className="font-semibold">{token.name}</div>
                      <div className="text-gray-400 text-sm">${token.symbol}</div>
                    </div>
                  </div>
                  <div className="mb-2">
                    <div className="flex justify-between text-xs text-gray-400 mb-1">
                      <span>Progress</span>
                      <span>{progress.toFixed(1)}%</span>
                    </div>
                    <div className="w-full bg-gray-800 rounded-full h-2">
                      <div className="bg-blue-500 h-2 rounded-full" style={{ width: `${progress}%` }} />
                    </div>
                  </div>
                  <div className="text-xs text-gray-500">
                    {token.eth_collected.toFixed(4)} ETH collected
                  </div>
                </a>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
