'use client';

import { usePrivy } from '@privy-io/react-auth';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';

export default function TokenPage() {
  const params = useParams();
  const address = Array.isArray(params?.address) ? params.address[0] : params?.address;
  const { authenticated, login, user } = usePrivy();
  const [token, setToken] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [buying, setBuying] = useState(false);
  const [amount, setAmount] = useState('0.001');
  const [txHash, setTxHash] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    if (!address) return;

    setLoading(true);
    fetch(`/api/token/${address}`)
      .then((res) => res.json())
      .then((data) => setToken(data))
      .catch(() => setToken(null))
      .finally(() => setLoading(false));
  }, [address]);

  const handleBuy = async () => {
    if (!authenticated) {
      login();
      return;
    }

    setBuying(true);
    setError('');
    setTxHash('');

    try {
      const res = await fetch('/api/buy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tokenAddress: address, amountEth: amount, userAddress: user?.wallet?.address }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Buy request failed');
      setTxHash(data.txHash);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setBuying(false);
    }
  };

  if (!address) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center text-white">
        Invalid token address
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-blue-500 animate-pulse text-xl">Loading...</div>
      </div>
    );
  }

  if (!token) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center text-white">
        Token not found
      </div>
    );
  }

  const progress = Math.min((token.eth_collected / 24) * 100, 100);

  return (
    <div className="min-h-screen bg-black text-white">
      <header className="border-b border-gray-800 px-4 py-3 flex items-center justify-between">
        <a href="/" className="flex items-center gap-2">
          <span className="text-xl font-bold text-blue-500">Base</span>
          <span className="text-xl font-bold text-cyan-400">Pump</span>
        </a>
        {!authenticated && (
          <button onClick={login} className="bg-blue-600 px-4 py-2 rounded-lg text-sm">
            Connect
          </button>
        )}
      </header>

      <div className="max-w-2xl mx-auto px-4 py-8">
        <div className="flex items-center gap-4 mb-6">
          <div className="w-16 h-16 rounded-full bg-blue-600 flex items-center justify-center text-2xl font-bold">
            {token.symbol?.slice(0, 2)}
          </div>
          <div>
            <h1 className="text-3xl font-bold">{token.name}</h1>
            <p className="text-gray-400 text-lg">${token.symbol}</p>
          </div>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 mb-4">
          <div className="flex justify-between text-sm text-gray-400 mb-2">
            <span>Bonding curve progress</span>
            <span>{progress.toFixed(1)}%</span>
          </div>
          <div className="w-full bg-gray-800 rounded-full h-3 mb-2">
            <div className="bg-blue-500 h-3 rounded-full transition-all" style={{ width: `${progress}%` }} />
          </div>
          <div className="flex justify-between text-xs text-gray-500">
            <span>{token.eth_collected?.toFixed(4)} ETH</span>
            <span>24 ETH target</span>
          </div>
          <p className="text-xs text-gray-500 mt-2">
            When the bonding curve reaches 24 ETH, liquidity migrates to Uniswap 🎓
          </p>
        </div>

        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-3">
            <div className="text-gray-400 text-xs mb-1">Contract</div>
            <div className="text-xs font-mono text-blue-400 break-all">{address}</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-3">
            <div className="text-gray-400 text-xs mb-1">Network</div>
            <div className="text-sm font-medium">Base Sepolia</div>
          </div>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <h2 className="font-semibold mb-3">Buy {token.symbol}</h2>
          <div className="flex gap-2 mb-3 flex-wrap">
            {['0.001', '0.005', '0.01', '0.05'].map((a) => (
              <button
                key={a}
                onClick={() => setAmount(a)}
                className={`px-3 py-1 rounded-lg text-sm ${amount === a ? 'bg-blue-600' : 'bg-gray-800 hover:bg-gray-700'}`}
              >
                {a} ETH
              </button>
            ))}
          </div>
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 mb-3 text-white"
            placeholder="Amount in ETH"
            step="0.001"
            min="0.001"
          />
          <button
            onClick={handleBuy}
            disabled={buying}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 py-3 rounded-lg font-semibold"
          >
            {buying ? 'Buying...' : authenticated ? `Buy ${token.symbol}` : 'Connect to Buy'}
          </button>

          {txHash && (
            <div className="mt-3 p-3 bg-green-900/30 border border-green-800 rounded-lg">
              <p className="text-green-400 text-sm">✅ Buy successful!</p>
              <a
                href={`https://sepolia.basescan.org/tx/${txHash}`}
                target="_blank"
                rel="noreferrer"
                className="text-blue-400 text-xs underline"
              >
                View transaction
              </a>
            </div>
          )}

          {error && (
            <div className="mt-3 p-3 bg-red-900/30 border border-red-800 rounded-lg">
              <p className="text-red-400 text-sm">❌ {error}</p>
            </div>
          )}
        </div>

        <a
          href={`https://sepolia.basescan.org/address/${address}`}
          target="_blank"
          rel="noreferrer"
          className="block text-center text-gray-500 text-sm mt-4 hover:text-gray-300"
        >
          View on BaseScan ↗
        </a>
      </div>
    </div>
  );
}
