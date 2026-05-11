'use client';

import { usePrivy } from '@privy-io/react-auth';
import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function CreateToken() {
  const { authenticated, login, user } = usePrivy();
  const router = useRouter();
  const [name, setName] = useState('');
  const [symbol, setSymbol] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleCreate = async () => {
    if (!authenticated) {
      login();
      return;
    }

    if (!name.trim() || !symbol.trim()) {
      setError('Name and symbol required');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const res = await fetch('/api/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.trim(),
          symbol: symbol.trim().toUpperCase(),
          userAddress: user?.wallet?.address,
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Token creation failed');
      router.push(`/token/${data.tokenAddress}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-black text-white">
      <header className="border-b border-gray-800 px-4 py-3 flex items-center justify-between">
        <a href="/" className="flex items-center gap-2">
          <span className="text-xl font-bold text-blue-500">Base</span>
          <span className="text-xl font-bold text-cyan-400">Pump</span>
        </a>
      </header>

      <div className="max-w-lg mx-auto px-4 py-12">
        <h1 className="text-3xl font-bold mb-2">Create a token</h1>
        <p className="text-gray-400 mb-8">
          Launch your token with a fair bonding curve. No presale, no rug.
        </p>

        <div className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Token Name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Pepe Coin"
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white focus:border-blue-500 outline-none"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">Token Symbol</label>
            <input
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              placeholder="e.g. PEPE"
              maxLength={10}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white focus:border-blue-500 outline-none"
            />
          </div>

          {error && (
            <div className="p-3 bg-red-900/30 border border-red-800 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}

          <button
            onClick={handleCreate}
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 py-4 rounded-xl font-bold text-lg mt-4"
          >
            {loading ? 'Deploying...' : authenticated ? 'Launch Token 🚀' : 'Connect Wallet'}
          </button>

          <p className="text-center text-gray-500 text-sm">
            Token creation is free. You only pay gas (~$0.001 on Base).
          </p>
        </div>
      </div>
    </div>
  );
}
