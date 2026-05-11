import { NextResponse } from 'next/server';
import { keccak256 } from 'viem';

const FACTORY = '0x228213e7df0516856b89311f78caded88789907e';
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
  return keccak256(new TextEncoder().encode(sig)).slice(2, 10);
}

async function getTokenInfo(address: string) {
  const call = async (sig: string) => {
    const selector = getSelector(sig);
    return rpc('eth_call', [{ to: address, data: '0x' + selector }, 'latest']);
  };

  try {
    const [nameHex, symbolHex, ethHex] = await Promise.all([
      call('name()'),
      call('symbol()'),
      call('ethCollected()'),
    ]);

    return {
      name: decodeString(nameHex),
      symbol: decodeString(symbolHex),
      eth_collected: ethHex ? parseInt(ethHex, 16) / 1e18 : 0,
    };
  } catch {
    return {
      name: 'Unknown',
      symbol: '???',
      eth_collected: 0,
    };
  }
}

export async function GET() {
  try {
    const blockHex = await rpc('eth_blockNumber', []);
    const current = parseInt(blockHex, 16);
    const fromBlock = '0x' + Math.max(0, current - 1900).toString(16);

    const topic = '0xd5d05a8421149c74fd223cfc823befb883babf9bf0b0e4d6bf9c8fdb70e59bb4';

    const logs = await rpc('eth_getLogs', [
      {
        address: FACTORY,
        topics: [topic],
        fromBlock,
        toBlock: 'latest',
      },
    ]);

    const tokens = await Promise.all(
      (logs as Array<any>).map(async (log) => {
        const address = '0x' + log.topics[1].slice(-40);
        const creator = '0x' + log.topics[2].slice(-40);
        const info = await getTokenInfo(address);
        return { address, creator, ...info };
      })
    );

    return NextResponse.json(tokens.reverse());
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
