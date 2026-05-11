import { NextResponse } from 'next/server';
import { keccak256, toBytes } from 'viem';

const RPC = 'https://sepolia.base.org';

async function rpc(method: string, params: unknown[]) {
  const res = await fetch(RPC, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ jsonrpc: '2.0', method, params, id: 1 }),
    cache: 'no-store',
  });

  const data = await res.json();
  if (data.error) throw new Error(data.error.message || 'RPC error');
  return data.result;
}

function decodeString(hex: string): string {
  if (!hex || hex === '0x' || hex.length < 130) return '';
  const data = hex.slice(2);
  const offset = parseInt(data.slice(0, 64), 16) * 2;
  const length = parseInt(data.slice(offset, offset + 64), 16);
  const raw = data.slice(offset + 64, offset + 64 + length * 2);
  return Buffer.from(raw, 'hex').toString('utf8');
}

function getSelector(sig: string) {
  return keccak256(toBytes(sig)).slice(2, 10);
}

async function getTokenInfo(address: string) {
  const call = async (sig: string) => {
    const selector = getSelector(sig);
    return rpc('eth_call', [{ to: address, data: `0x${selector}` }, 'latest']);
  };

  try {
    const [nameHex, symbolHex, ethHex, supplyHex] = await Promise.all([
      call('name()'),
      call('symbol()'),
      call('ethCollected()'),
      call('totalSupply()'),
    ]);

    return {
      name: decodeString(nameHex),
      symbol: decodeString(symbolHex),
      eth_collected: ethHex ? parseInt(ethHex, 16) / 1e18 : 0,
      total_supply: supplyHex ? parseInt(supplyHex, 16) / 1e18 : 0,
    };
  } catch {
    return {
      name: 'Unknown',
      symbol: '???',
      eth_collected: 0,
      total_supply: 0,
    };
  }
}

export async function GET(
  _: Request,
  { params }: { params: Promise<{ address: string }> }
) {
  try {
    const resolvedParams = await params;
    const token = await getTokenInfo(resolvedParams.address);
    return NextResponse.json({ address: resolvedParams.address, ...token });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
